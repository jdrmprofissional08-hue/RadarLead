"""Gerenciador de conexão com o MySQL (BACK-07, versão MySQL).

Mesmo uso do GerenciadorConexao (PostgreSQL):

    gerenciador = GerenciadorConexaoMySQL("mysql://root:senha@localhost:3306/radarlead")

    with gerenciador as ger:
        with ger.cursor() as cur:
            cur.execute("INSERT ...")
    # saiu do with sem erro  -> commit, e a conexão é fechada
    # saiu do with com erro  -> rollback, a conexão é fechada e o erro continua

Pontos importantes:
    - Cada ``with`` abre uma conexão nova, é uma transação e fecha a conexão.
    - Falhas de conexão (servidor fora do ar, senha errada...) e de
      commit/rollback viram PersistenciaError, com a causa original anexada.
    - Não é seguro entre threads: use um gerenciador por thread.

O primeiro argumento é uma URL ("mysql://usuario:senha@host:porta/banco";
usuário e senha com caracteres especiais devem vir codificados, ex.: @ = %40).
Argumentos nomeados (host, port, user, password, database...) valem no lugar da
URL ou a complementam. Sem nada, usa 127.0.0.1:3306 com o usuário root.

Usa o PyMySQL (Python puro, sem compilar nada). A autenticação padrão do
MySQL 8 (caching_sha2_password) exige o pacote "cryptography", que o
requirements.txt já inclui (PyMySQL[rsa]).
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import unquote, urlsplit

import pymysql

from src.excecoes import PersistenciaError

TEMPO_LIMITE_PADRAO = 10  # segundos para estabelecer a conexão
PORTA_PADRAO = 3306


def parametros_da_url(url: str) -> dict:
    """Converte 'mysql://usuario:senha@host:porta/banco' em argumentos do PyMySQL."""
    partes = urlsplit(url)
    if partes.scheme not in ("mysql", "mysql+pymysql"):
        raise PersistenciaError(
            "URL do MySQL inválida: deve começar com mysql:// "
            "(exemplo: mysql://usuario:senha@localhost:3306/radarlead)"
        )
    try:
        porta = partes.port
    except ValueError as erro:
        raise PersistenciaError(f"URL do MySQL com porta inválida: {erro}") from erro

    parametros = {}
    if partes.hostname:
        parametros["host"] = partes.hostname
    if porta:
        parametros["port"] = porta
    if partes.username:
        parametros["user"] = unquote(partes.username)
    if partes.password:
        parametros["password"] = unquote(partes.password)
    banco = partes.path.lstrip("/")
    if banco:
        parametros["database"] = unquote(banco)
    return parametros


class GerenciadorConexaoMySQL:

    def __init__(self, url: Optional[str] = None, **parametros):
        base = {"host": "127.0.0.1", "port": PORTA_PADRAO, "user": "root"}
        if url:
            base.update(parametros_da_url(url))
        base.update(parametros)
        base.setdefault("connect_timeout", TEMPO_LIMITE_PADRAO)
        # o commit é sempre explícito; utf8mb4 para aceitar qualquer acento
        base["charset"] = "utf8mb4"
        base["autocommit"] = False
        self._parametros = base
        self._conexao = None

    # --- Estado ----------------------------------------------------------

    @property
    def aberta(self) -> bool:
        return self._conexao is not None and bool(self._conexao.open)

    # --- Abrir e fechar --------------------------------------------------

    def abrir(self) -> "GerenciadorConexaoMySQL":
        """Abre a conexão. Levanta PersistenciaError se não conseguir."""
        if self.aberta:
            raise PersistenciaError("A conexão já está aberta")

        try:
            self._conexao = pymysql.connect(**self._parametros)
        except pymysql.MySQLError as erro:
            self._conexao = None
            raise PersistenciaError(
                f"Não foi possível conectar ao MySQL: {self._resumo(erro)}"
            ) from erro
        except (OSError, RuntimeError) as erro:
            # RuntimeError: falta o pacote "cryptography" na autenticação do MySQL 8
            self._conexao = None
            raise PersistenciaError(
                f"Não foi possível conectar ao MySQL: {self._resumo(erro)}"
            ) from erro

        return self

    def fechar(self) -> None:
        """Fecha a conexão (sem commit). Não faz nada se já estiver fechada."""
        conexao, self._conexao = self._conexao, None
        if conexao is None:
            return

        try:
            conexao.close()
        except Exception:  # fechar nunca deve esconder o erro de quem chamou
            pass

    # --- Transação -------------------------------------------------------

    def commit(self) -> None:
        conexao = self._conexao_ativa()
        try:
            conexao.commit()
        except pymysql.MySQLError as erro:
            raise PersistenciaError(
                f"Falha ao confirmar a transação (commit): {self._resumo(erro)}"
            ) from erro

    def rollback(self) -> None:
        conexao = self._conexao_ativa()
        try:
            conexao.rollback()
        except pymysql.MySQLError as erro:
            raise PersistenciaError(
                f"Falha ao desfazer a transação (rollback): {self._resumo(erro)}"
            ) from erro

    def cursor(self):
        """Cursor da conexão aberta (pode ser usado em ``with``)."""
        conexao = self._conexao_ativa()
        try:
            return conexao.cursor()
        except pymysql.MySQLError as erro:
            raise PersistenciaError(
                f"Não foi possível criar o cursor: {self._resumo(erro)}"
            ) from erro

    # --- Gerenciador de contexto ----------------------------------------

    def __enter__(self) -> "GerenciadorConexaoMySQL":
        return self.abrir()

    def __exit__(self, tipo_erro, erro, rastro) -> bool:
        try:
            if tipo_erro is None:
                try:
                    self.commit()
                except PersistenciaError:
                    self._tentar_rollback()
                    raise
            else:
                self._tentar_rollback()
        finally:
            self.fechar()

        return False  # nunca engole o erro de quem usou o with

    # --- Internos --------------------------------------------------------

    def _conexao_ativa(self):
        if not self.aberta:
            raise PersistenciaError(
                "A conexão não está aberta (use o gerenciador dentro de um 'with')"
            )
        return self._conexao

    def _tentar_rollback(self) -> None:
        if self.aberta:
            try:
                self._conexao.rollback()
            except Exception:
                pass

    @staticmethod
    def _resumo(erro: Exception) -> str:
        """Mensagem do servidor, sem a senha (que nunca é incluída)."""
        args = getattr(erro, "args", ())
        if len(args) >= 2 and isinstance(args[0], int):
            return f"{str(args[1]).strip().splitlines()[0]} (erro {args[0]})"
        texto = str(erro).strip()
        return texto.splitlines()[0] if texto else type(erro).__name__

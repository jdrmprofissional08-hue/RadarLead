"""Gerenciador de conexão com o PostgreSQL (BACK-07).

Uso como gerenciador de contexto:

    gerenciador = GerenciadorConexao("host=localhost dbname=radarlead user=...")

    with gerenciador as ger:
        with ger.cursor() as cur:
            cur.execute("INSERT ...")
    # saiu do with sem erro  -> commit, e a conexão é fechada
    # saiu do with com erro  -> rollback, a conexão é fechada e o erro continua

Pontos importantes:
    - O objeto é reutilizável: cada ``with`` abre uma conexão nova e a fecha ao
      sair. Cada ``with`` é uma transação.
    - Dentro do ``with`` também dá para chamar ``commit()`` e ``rollback()``
      na mão (por exemplo, para confirmar uma parte do trabalho e seguir).
    - Falhas de conexão (servidor fora do ar, senha errada...) e de
      commit/rollback viram PersistenciaError, com a causa original anexada.
    - Não é seguro entre threads: use um gerenciador por thread.

O primeiro argumento é um DSN do libpq ("host=... dbname=...") ou uma URL
("postgresql://usuario:senha@host/banco"). Sem ele, o psycopg2 usa as
variáveis de ambiente padrão do PostgreSQL (PGHOST, PGDATABASE, PGUSER...).
Argumentos nomeados extras vão direto para psycopg2.connect().
"""

from __future__ import annotations

from typing import Optional

import psycopg2

from src.excecoes import PersistenciaError

TEMPO_LIMITE_PADRAO = 10  # segundos para estabelecer a conexão


class GerenciadorConexao:

    def __init__(self, dsn: Optional[str] = None, **parametros):
        self._dsn = dsn
        self._parametros = {"connect_timeout": TEMPO_LIMITE_PADRAO, **parametros}
        self._conexao = None

    # --- Estado ----------------------------------------------------------

    @property
    def aberta(self) -> bool:
        return self._conexao is not None and not self._conexao.closed

    # --- Abrir e fechar --------------------------------------------------

    def abrir(self) -> "GerenciadorConexao":
        """Abre a conexão. Levanta PersistenciaError se não conseguir."""
        if self.aberta:
            raise PersistenciaError("A conexão já está aberta")

        try:
            self._conexao = psycopg2.connect(self._dsn, **self._parametros)
        except psycopg2.Error as erro:
            self._conexao = None
            raise PersistenciaError(
                f"Não foi possível conectar ao PostgreSQL: {self._resumo(erro)}"
            ) from erro
        except UnicodeDecodeError as erro:
            self._conexao = None
            raise PersistenciaError(
                "Não foi possível conectar ao PostgreSQL: o servidor recusou a "
                "conexão (confira host, porta, banco, usuário e senha); a "
                "mensagem dele veio em uma codificação que não é UTF-8"
            ) from erro
        
        return self

    def fechar(self) -> None:
        """Fecha a conexão (sem commit). Não faz nada se já estiver fechada."""
        conexao, self._conexao = self._conexao, None
        if conexao is None or conexao.closed:
            return

        try:
            conexao.close()
        except psycopg2.Error:
            pass  # fechar nunca deve esconder o erro de quem chamou

    # --- Transação -------------------------------------------------------

    def commit(self) -> None:
        conexao = self._conexao_ativa()
        try:
            conexao.commit()
        except psycopg2.Error as erro:
            raise PersistenciaError(
                f"Falha ao confirmar a transação (commit): {self._resumo(erro)}"
            ) from erro

    def rollback(self) -> None:
        conexao = self._conexao_ativa()
        try:
            conexao.rollback()
        except psycopg2.Error as erro:
            raise PersistenciaError(
                f"Falha ao desfazer a transação (rollback): {self._resumo(erro)}"
            ) from erro

    def cursor(self):
        """Cursor da conexão aberta (pode ser usado em ``with``)."""
        conexao = self._conexao_ativa()
        try:
            return conexao.cursor()
        except psycopg2.Error as erro:
            raise PersistenciaError(
                f"Não foi possível criar o cursor: {self._resumo(erro)}"
            ) from erro

    # --- Gerenciador de contexto ----------------------------------------

    def __enter__(self) -> "GerenciadorConexao":
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
                # o erro original é o que importa: se o rollback também
                # falhar, o servidor já descarta a transação ao fechar
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
            except psycopg2.Error:
                pass

    @staticmethod
    def _resumo(erro: Exception) -> str:
        """Primeira linha da mensagem do psycopg2 (sem a senha, nunca incluída)."""
        texto = str(erro).strip()
        return texto.splitlines()[0] if texto else type(erro).__name__

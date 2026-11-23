"""Apoio aos testes que usam um MySQL de verdade.

Como ligar: defina RADARLEAD_TEST_MYSQL_URL com a conexão de um servidor de
TESTE (sem o nome do banco), por exemplo:

    export RADARLEAD_TEST_MYSQL_URL="mysql://root:senha@127.0.0.1:3306"
    # PowerShell:  $env:RADARLEAD_TEST_MYSQL_URL = "mysql://root:senha@127.0.0.1:3306"

O usuário precisa poder criar e apagar bancos e triggers.

Sem a variável (ou sem PyMySQL, ou com o servidor fora do ar) os testes que
dependem do banco são PULADOS, e o resto da suíte roda normalmente.

Segurança: tudo acontece em um banco próprio, "radarlead_teste", que é apagado
e recriado no começo e removido no fim. Nenhum outro banco é tocado.
"""

import atexit
import os
import unittest
from pathlib import Path

try:
    import pymysql
except ImportError:  # pragma: no cover
    pymysql = None

from src.persistencia.conexao_mysql import GerenciadorConexaoMySQL

BANCO = "radarlead_teste"
URL = os.environ.get("RADARLEAD_TEST_MYSQL_URL")
RAIZ = Path(__file__).resolve().parent.parent
SQL_MYSQL = RAIZ / "sql" / "mysql"

_estado = {"disponivel": None, "pronto": False}


def _conectar_cru(banco=None):
    """Conexão direta (autocommit), usada só para criar/apagar o banco de teste."""
    from src.persistencia.conexao_mysql import parametros_da_url

    parametros = {"host": "127.0.0.1", "port": 3306, "user": "root"}
    parametros.update(parametros_da_url(URL))
    parametros.pop("database", None)
    if banco:
        parametros["database"] = banco
    return pymysql.connect(
        charset="utf8mb4", autocommit=True, connect_timeout=3, **parametros
    )


def disponivel() -> bool:
    if _estado["disponivel"] is None:
        ok = False
        if pymysql is not None and URL:
            try:
                _conectar_cru().close()
                ok = True
            except Exception:
                ok = False
        _estado["disponivel"] = ok
    return _estado["disponivel"]


requer_mysql = unittest.skipUnless(
    # avaliado na importação do módulo de testes
    disponivel(),
    "MySQL de teste indisponível (defina RADARLEAD_TEST_MYSQL_URL e instale PyMySQL)",
)


def gerenciador() -> GerenciadorConexaoMySQL:
    """Gerenciador que enxerga só o banco de teste."""
    return GerenciadorConexaoMySQL(URL, database=BANCO)


def dividir_script(texto: str) -> list[str]:
    """Separa um script SQL em comandos, respeitando 'DELIMITER'.

    (O cliente do MySQL entende DELIMITER; o servidor não. Os triggers e a
    função do schema.sql precisam dele porque têm ';' dentro do corpo.)
    """
    comandos = []
    delimitador = ";"
    atual: list[str] = []

    for linha in texto.splitlines():
        limpa = linha.strip()
        if limpa.upper().startswith("DELIMITER "):
            delimitador = limpa.split(None, 1)[1].strip()
            continue
        if not atual and (not limpa or limpa.startswith("--")):
            continue
        atual.append(linha)
        if limpa.endswith(delimitador):
            comando = "\n".join(atual).rstrip()
            comando = comando[: -len(delimitador)].rstrip()
            if comando:
                comandos.append(comando)
            atual = []

    if "".join(atual).strip():
        comandos.append("\n".join(atual).strip())
    return comandos


def executar_script(cur, arquivo: Path) -> None:
    for comando in dividir_script(arquivo.read_text(encoding="utf-8")):
        cur.execute(comando)


def preparar_banco() -> None:
    """Recria o banco de teste com o DDL do projeto (uma vez por processo)."""
    if _estado["pronto"]:
        return
    conexao = _conectar_cru()
    try:
        with conexao.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS {BANCO}")
            cur.execute(f"CREATE DATABASE {BANCO} CHARACTER SET utf8mb4")
            cur.execute(f"USE {BANCO}")
            executar_script(cur, SQL_MYSQL / "schema.sql")
    finally:
        conexao.close()
    _estado["pronto"] = True
    atexit.register(remover_banco)


def remover_banco() -> None:
    if not _estado["pronto"]:
        return
    try:
        conexao = _conectar_cru()
        try:
            with conexao.cursor() as cur:
                cur.execute(f"DROP DATABASE IF EXISTS {BANCO}")
        finally:
            conexao.close()
    except Exception:
        pass


def executar(sql: str, parametros=None):
    """Roda um SQL no banco de teste (com commit) e devolve as linhas, se houver."""
    with gerenciador() as ger:
        with ger.cursor() as cur:
            cur.execute(sql, parametros)
            return list(cur.fetchall()) if cur.description else None


def resetar_dados() -> None:
    """Esvazia todas as tabelas, zera os ids e recarrega os domínios de teste."""
    with gerenciador() as ger:
        with ger.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                (BANCO,),
            )
            tabelas = [linha[0] for linha in cur.fetchall()]
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            for tabela in tabelas:
                cur.execute(f"TRUNCATE TABLE `{tabela}`")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")

            executar_script(cur, SQL_MYSQL / "seed_dominios.sql")
            cur.execute(
                """INSERT INTO municipio (codigo_ibge, nome, uf) VALUES
                       ('5208707', 'Goiânia', 'GO'),
                       ('5205109', 'Catalão', 'GO')"""
            )
            cur.execute(
                """INSERT INTO cnae (codigo, descricao) VALUES
                       ('6204000', 'Consultoria em tecnologia da informação'),
                       ('5611201', 'Restaurantes e similares'),
                       ('4520001', 'Manutenção e reparação mecânica de veículos'),
                       ('1111111', 'CNAE de teste')"""
            )


def criar_repositorio_mysql(**argumentos):
    """Repositório MySQL sobre o banco de teste, já com dados zerados."""
    from src.persistencia.repositorio_mysql import RepositorioMySQL

    preparar_banco()
    resetar_dados()
    return RepositorioMySQL(gerenciador(), **argumentos)

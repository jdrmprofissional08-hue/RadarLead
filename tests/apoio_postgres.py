"""Apoio aos testes que usam um PostgreSQL de verdade.

Como ligar: defina RADARLEAD_TEST_DSN com a conexão de um banco de TESTE, por
exemplo:

    export RADARLEAD_TEST_DSN="host=127.0.0.1 dbname=radarlead_teste user=radarlead password=radarlead"

Sem a variável (ou sem psycopg2, ou com o servidor fora do ar) os testes que
dependem do banco são PULADOS, e o resto da suíte roda normalmente.

Segurança: tudo acontece em um schema próprio (radarlead_teste), que é
apagado e recriado no começo e removido no fim. Nenhuma tabela do schema
public é tocada.
"""

import atexit
import os
import unittest
from pathlib import Path

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None

from src.persistencia.conexao import GerenciadorConexao

SCHEMA = "radarlead_teste"
DSN = os.environ.get("RADARLEAD_TEST_DSN")
RAIZ = Path(__file__).resolve().parent.parent

_estado = {"disponivel": None, "pronto": False}


def _conectar_cru():
    conexao = psycopg2.connect(DSN, connect_timeout=3)
    conexao.autocommit = True
    return conexao


def disponivel() -> bool:
    if _estado["disponivel"] is None:
        ok = False
        if psycopg2 is not None and DSN:
            try:
                _conectar_cru().close()
                ok = True
            except psycopg2.Error:
                ok = False
        _estado["disponivel"] = ok
    return _estado["disponivel"]


requer_postgres = unittest.skipUnless(
    # avaliado na importação do módulo de testes
    disponivel(),
    "PostgreSQL de teste indisponível (defina RADARLEAD_TEST_DSN e instale psycopg2)",
)


def gerenciador() -> GerenciadorConexao:
    """Gerenciador que enxerga só o schema de teste."""
    return GerenciadorConexao(DSN, options=f"-c search_path={SCHEMA}")


def preparar_schema() -> None:
    """Recria o schema de teste com o DDL do projeto (uma vez por processo)."""
    if _estado["pronto"]:
        return
    conexao = _conectar_cru()
    try:
        with conexao.cursor() as cur:
            cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            cur.execute(f"SET search_path TO {SCHEMA}")
            cur.execute((RAIZ / "sql" / "schema.sql").read_text(encoding="utf-8"))
    finally:
        conexao.close()
    _estado["pronto"] = True
    atexit.register(remover_schema)


def remover_schema() -> None:
    if not _estado["pronto"]:
        return
    try:
        conexao = _conectar_cru()
        try:
            with conexao.cursor() as cur:
                cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        finally:
            conexao.close()
    except Exception:
        pass


def executar(sql: str, parametros=None):
    """Roda um SQL no schema de teste (com commit) e devolve as linhas, se houver."""
    with gerenciador() as ger:
        with ger.cursor() as cur:
            cur.execute(sql, parametros)
            return cur.fetchall() if cur.description else None


def resetar_dados() -> None:
    """Esvazia todas as tabelas, zera os ids e recarrega os domínios de teste."""
    with gerenciador() as ger:
        with ger.cursor() as cur:
            cur.execute(
                """SELECT string_agg(quote_ident(tablename), ', ')
                     FROM pg_tables WHERE schemaname = %s""",
                (SCHEMA,),
            )
            cur.execute(f"TRUNCATE {cur.fetchone()[0]} RESTART IDENTITY CASCADE")
            cur.execute((RAIZ / "sql" / "seed_dominios.sql").read_text(encoding="utf-8"))
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


def criar_repositorio_postgres(**argumentos):
    """Repositório PostgreSQL sobre o schema de teste, já com dados zerados."""
    from src.persistencia.repositorio_postgres import RepositorioPostgres

    preparar_schema()
    resetar_dados()
    return RepositorioPostgres(gerenciador(), **argumentos)

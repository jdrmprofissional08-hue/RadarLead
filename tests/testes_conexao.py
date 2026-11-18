"""Testes do gerenciador de conexão (BACK-07).

Parte dos testes usa um psycopg2 simulado (sempre roda); a outra usa um
PostgreSQL real (ver tests/apoio_postgres.py) e é pulada se ele não existir.
"""

import unittest
from unittest import mock

import psycopg2

from src.excecoes import PersistenciaError
from src.persistencia.conexao import GerenciadorConexao
from tests import apoio_postgres


def conexao_falsa(**falhas):
    """Conexão simulada; falhas={'commit': erro} faz o método levantar o erro."""
    conexao = mock.MagicMock()
    conexao.closed = 0
    for nome, erro in falhas.items():
        getattr(conexao, nome).side_effect = erro

    def fechar():
        conexao.closed = 1
    conexao.close.side_effect = fechar
    return conexao


class TestGerenciadorSimulado(unittest.TestCase):

    def usar(self, conexao):
        patch = mock.patch("src.persistencia.conexao.psycopg2.connect",
                           return_value=conexao)
        self.connect = patch.start()
        self.addCleanup(patch.stop)

    def test_saida_normal_faz_commit_e_fecha(self):
        conexao = conexao_falsa()
        self.usar(conexao)

        with GerenciadorConexao("dsn") as ger:
            self.assertTrue(ger.aberta)

        conexao.commit.assert_called_once()
        conexao.rollback.assert_not_called()
        conexao.close.assert_called_once()

    def test_erro_dentro_do_with_faz_rollback_e_propaga(self):
        conexao = conexao_falsa()
        self.usar(conexao)
        ger = GerenciadorConexao("dsn")

        with self.assertRaises(ValueError):
            with ger:
                raise ValueError("falhou")

        conexao.commit.assert_not_called()
        conexao.rollback.assert_called_once()
        conexao.close.assert_called_once()
        self.assertFalse(ger.aberta)

    def test_falha_no_commit_vira_persistencia_error_com_rollback(self):
        conexao = conexao_falsa(commit=psycopg2.OperationalError("disco cheio"))
        self.usar(conexao)

        with self.assertRaises(PersistenciaError) as ctx:
            with GerenciadorConexao("dsn"):
                pass

        self.assertIn("commit", str(ctx.exception))
        self.assertIsInstance(ctx.exception.__cause__, psycopg2.OperationalError)
        conexao.rollback.assert_called_once()
        conexao.close.assert_called_once()

    def test_falha_no_rollback_nao_esconde_o_erro_original(self):
        conexao = conexao_falsa(rollback=psycopg2.OperationalError("caiu"))
        self.usar(conexao)

        with self.assertRaises(ValueError):
            with GerenciadorConexao("dsn"):
                raise ValueError("erro original")

        conexao.close.assert_called_once()

    def test_falha_ao_fechar_e_ignorada(self):
        conexao = conexao_falsa(close=psycopg2.OperationalError("x"))
        self.usar(conexao)

        with GerenciadorConexao("dsn"):
            pass  # não levanta

    def test_conexao_recusada_vira_persistencia_error(self):
        with mock.patch(
            "src.persistencia.conexao.psycopg2.connect",
            side_effect=psycopg2.OperationalError(
                "connection to server at \"localhost\", port 5432 failed: "
                "Connection refused\n\tIs the server running?"
            ),
        ):
            ger = GerenciadorConexao("dsn")
            with self.assertRaises(PersistenciaError) as ctx:
                with ger:
                    self.fail("não devia entrar no with")

        self.assertIn("Connection refused", str(ctx.exception))
        self.assertNotIn("\n", str(ctx.exception))
        self.assertFalse(ger.aberta)

    def test_commit_e_rollback_manuais(self):
        conexao = conexao_falsa()
        self.usar(conexao)

        with GerenciadorConexao("dsn") as ger:
            ger.commit()
            ger.rollback()

        self.assertEqual(conexao.commit.call_count, 2)  # manual + saída
        self.assertEqual(conexao.rollback.call_count, 1)

    def test_falha_no_commit_manual_vira_persistencia_error(self):
        conexao = conexao_falsa(commit=psycopg2.OperationalError("x"))
        self.usar(conexao)

        with self.assertRaises(PersistenciaError):
            with GerenciadorConexao("dsn") as ger:
                ger.commit()

    def test_falha_no_rollback_manual_vira_persistencia_error(self):
        conexao = conexao_falsa(rollback=psycopg2.InterfaceError("x"))
        self.usar(conexao)

        with GerenciadorConexao("dsn") as ger:
            with self.assertRaises(PersistenciaError):
                ger.rollback()

    def test_operacoes_fora_do_with_levantam_erro_claro(self):
        ger = GerenciadorConexao("dsn")
        for operacao in (ger.commit, ger.rollback, ger.cursor):
            with self.subTest(operacao.__name__):
                with self.assertRaises(PersistenciaError):
                    operacao()

    def test_abrir_duas_vezes_e_erro(self):
        self.usar(conexao_falsa())
        ger = GerenciadorConexao("dsn")

        with ger:
            with self.assertRaises(PersistenciaError):
                ger.abrir()

    def test_pode_reutilizar_depois_de_fechar(self):
        self.usar(conexao_falsa())
        self.connect.side_effect = lambda *a, **k: conexao_falsa()
        ger = GerenciadorConexao("dsn")

        with ger:
            pass
        with ger:
            self.assertTrue(ger.aberta)

        self.assertEqual(self.connect.call_count, 2)

    def test_repassa_dsn_e_parametros_e_define_tempo_limite(self):
        self.usar(conexao_falsa())

        with GerenciadorConexao("dbname=x", sslmode="disable"):
            pass

        self.connect.assert_called_once_with(
            "dbname=x", connect_timeout=10, sslmode="disable"
        )

    def test_fechar_sem_abrir_nao_faz_nada(self):
        GerenciadorConexao("dsn").fechar()


@apoio_postgres.requer_postgres
class TestGerenciadorComBancoReal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        apoio_postgres.preparar_schema()

    def setUp(self):
        apoio_postgres.resetar_dados()

    def contar_cnaes(self):
        return apoio_postgres.executar("SELECT count(*) FROM cnae")[0][0]

    def test_commit_grava_de_verdade(self):
        antes = self.contar_cnaes()

        with apoio_postgres.gerenciador() as ger:
            with ger.cursor() as cur:
                cur.execute("INSERT INTO cnae VALUES ('9999999', 'Novo')")

        self.assertEqual(self.contar_cnaes(), antes + 1)

    def test_erro_desfaz_o_que_foi_gravado(self):
        antes = self.contar_cnaes()

        with self.assertRaises(RuntimeError):
            with apoio_postgres.gerenciador() as ger:
                with ger.cursor() as cur:
                    cur.execute("INSERT INTO cnae VALUES ('9999999', 'Novo')")
                raise RuntimeError("falhou depois do insert")

        self.assertEqual(self.contar_cnaes(), antes)

    def test_rollback_manual_descarta_so_o_que_veio_depois_do_commit(self):
        antes = self.contar_cnaes()

        with apoio_postgres.gerenciador() as ger:
            with ger.cursor() as cur:
                cur.execute("INSERT INTO cnae VALUES ('9999991', 'Fica')")
                ger.commit()
                cur.execute("INSERT INTO cnae VALUES ('9999992', 'Some')")
                ger.rollback()

        self.assertEqual(self.contar_cnaes(), antes + 1)

    def test_erro_de_sql_dentro_do_with_desfaz_tudo_e_propaga(self):
        antes = self.contar_cnaes()

        with self.assertRaises(psycopg2.errors.UniqueViolation):
            with apoio_postgres.gerenciador() as ger:
                with ger.cursor() as cur:
                    cur.execute("INSERT INTO cnae VALUES ('9999999', 'A')")
                    cur.execute("INSERT INTO cnae VALUES ('9999999', 'B')")

        self.assertEqual(self.contar_cnaes(), antes)

    def test_conexao_fica_fechada_depois_do_with(self):
        ger = apoio_postgres.gerenciador()
        with ger:
            self.assertTrue(ger.aberta)
        self.assertFalse(ger.aberta)

    def test_servidor_recusando_conexao(self):
        ger = GerenciadorConexao(
            "host=127.0.0.1 port=1 dbname=x user=x", connect_timeout=2
        )
        with self.assertRaises(PersistenciaError):
            with ger:
                pass

    def test_senha_errada(self):
        import re
        dsn = re.sub(r"password=\S+", "password=senha-errada", apoio_postgres.DSN)
        if "password=" not in dsn:
            self.skipTest("o DSN de teste não usa senha")

        with self.assertRaises(PersistenciaError) as ctx:
            with GerenciadorConexao(dsn):
                pass
        self.assertNotIn("senha-errada", str(ctx.exception))

    def test_banco_inexistente(self):
        import re
        dsn = re.sub(r"dbname=\S+", "dbname=banco_que_nao_existe", apoio_postgres.DSN)

        with self.assertRaises(PersistenciaError):
            with GerenciadorConexao(dsn):
                pass


if __name__ == "__main__":
    unittest.main()

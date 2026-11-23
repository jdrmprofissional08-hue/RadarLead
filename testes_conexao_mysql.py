"""Testes do gerenciador de conexão (BACK-07).

Parte dos testes usa um PyMySQL simulado (sempre roda); a outra usa um
MySQL real (ver tests/apoio_mysql.py) e é pulada se ele não existir.
"""

import unittest
from unittest import mock

import pymysql

from src.excecoes import PersistenciaError
from src.persistencia.conexao_mysql import GerenciadorConexaoMySQL, parametros_da_url
from tests import apoio_mysql


def conexao_falsa(**falhas):
    """Conexão simulada; falhas={'commit': erro} faz o método levantar o erro."""
    conexao = mock.MagicMock()
    conexao.open = True
    for nome, erro in falhas.items():
        getattr(conexao, nome).side_effect = erro

    def fechar():
        conexao.open = False
    conexao.close.side_effect = fechar
    return conexao


class TestGerenciadorSimulado(unittest.TestCase):

    def usar(self, conexao):
        patch = mock.patch("src.persistencia.conexao_mysql.pymysql.connect",
                           return_value=conexao)
        self.connect = patch.start()
        self.addCleanup(patch.stop)

    def test_saida_normal_faz_commit_e_fecha(self):
        conexao = conexao_falsa()
        self.usar(conexao)

        with GerenciadorConexaoMySQL("mysql://u:p@h/b") as ger:
            self.assertTrue(ger.aberta)

        conexao.commit.assert_called_once()
        conexao.rollback.assert_not_called()
        conexao.close.assert_called_once()

    def test_erro_dentro_do_with_faz_rollback_e_propaga(self):
        conexao = conexao_falsa()
        self.usar(conexao)
        ger = GerenciadorConexaoMySQL("mysql://u:p@h/b")

        with self.assertRaises(ValueError):
            with ger:
                raise ValueError("falhou")

        conexao.commit.assert_not_called()
        conexao.rollback.assert_called_once()
        conexao.close.assert_called_once()
        self.assertFalse(ger.aberta)

    def test_falha_no_commit_vira_persistencia_error_com_rollback(self):
        conexao = conexao_falsa(commit=pymysql.err.OperationalError("disco cheio"))
        self.usar(conexao)

        with self.assertRaises(PersistenciaError) as ctx:
            with GerenciadorConexaoMySQL("mysql://u:p@h/b"):
                pass

        self.assertIn("commit", str(ctx.exception))
        self.assertIsInstance(ctx.exception.__cause__, pymysql.err.OperationalError)
        conexao.rollback.assert_called_once()
        conexao.close.assert_called_once()

    def test_falha_no_rollback_nao_esconde_o_erro_original(self):
        conexao = conexao_falsa(rollback=pymysql.err.OperationalError("caiu"))
        self.usar(conexao)

        with self.assertRaises(ValueError):
            with GerenciadorConexaoMySQL("mysql://u:p@h/b"):
                raise ValueError("erro original")

        conexao.close.assert_called_once()

    def test_falha_ao_fechar_e_ignorada(self):
        conexao = conexao_falsa(close=pymysql.err.OperationalError("x"))
        self.usar(conexao)

        with GerenciadorConexaoMySQL("mysql://u:p@h/b"):
            pass  # não levanta

    def test_conexao_recusada_vira_persistencia_error(self):
        with mock.patch(
            "src.persistencia.conexao_mysql.pymysql.connect",
            side_effect=pymysql.err.OperationalError(
                2003, "Can't connect to MySQL server on '127.0.0.1' ([Errno 111] "
                "Connection refused)"
            ),
        ):
            ger = GerenciadorConexaoMySQL("mysql://u:p@h/b")
            with self.assertRaises(PersistenciaError) as ctx:
                with ger:
                    self.fail("não devia entrar no with")

        self.assertIn("Connection refused", str(ctx.exception))
        self.assertIn("2003", str(ctx.exception))
        self.assertNotIn("\n", str(ctx.exception))
        self.assertFalse(ger.aberta)

    def test_commit_e_rollback_manuais(self):
        conexao = conexao_falsa()
        self.usar(conexao)

        with GerenciadorConexaoMySQL("mysql://u:p@h/b") as ger:
            ger.commit()
            ger.rollback()

        self.assertEqual(conexao.commit.call_count, 2)  # manual + saída
        self.assertEqual(conexao.rollback.call_count, 1)

    def test_falha_no_commit_manual_vira_persistencia_error(self):
        conexao = conexao_falsa(commit=pymysql.err.OperationalError("x"))
        self.usar(conexao)

        with self.assertRaises(PersistenciaError):
            with GerenciadorConexaoMySQL("mysql://u:p@h/b") as ger:
                ger.commit()

    def test_falha_no_rollback_manual_vira_persistencia_error(self):
        conexao = conexao_falsa(rollback=pymysql.err.InterfaceError("x"))
        self.usar(conexao)

        with GerenciadorConexaoMySQL("mysql://u:p@h/b") as ger:
            with self.assertRaises(PersistenciaError):
                ger.rollback()

    def test_operacoes_fora_do_with_levantam_erro_claro(self):
        ger = GerenciadorConexaoMySQL("mysql://u:p@h/b")
        for operacao in (ger.commit, ger.rollback, ger.cursor):
            with self.subTest(operacao.__name__):
                with self.assertRaises(PersistenciaError):
                    operacao()

    def test_abrir_duas_vezes_e_erro(self):
        self.usar(conexao_falsa())
        ger = GerenciadorConexaoMySQL("mysql://u:p@h/b")

        with ger:
            with self.assertRaises(PersistenciaError):
                ger.abrir()

    def test_pode_reutilizar_depois_de_fechar(self):
        self.usar(conexao_falsa())
        self.connect.side_effect = lambda *a, **k: conexao_falsa()
        ger = GerenciadorConexaoMySQL("mysql://u:p@h/b")

        with ger:
            pass
        with ger:
            self.assertTrue(ger.aberta)

        self.assertEqual(self.connect.call_count, 2)

    def test_repassa_parametros_da_url_e_define_padroes(self):
        self.usar(conexao_falsa())

        with GerenciadorConexaoMySQL("mysql://ana:p%40ss%3Aw@db.exemplo:3307/radarlead"):
            pass

        self.connect.assert_called_once_with(
            host="db.exemplo", port=3307, user="ana", password="p@ss:w",
            database="radarlead", connect_timeout=10, charset="utf8mb4",
            autocommit=False,
        )

    def test_argumentos_nomeados_vencem_a_url_e_ha_padroes_sem_url(self):
        self.usar(conexao_falsa())

        with GerenciadorConexaoMySQL(database="x", connect_timeout=2):
            pass

        self.connect.assert_called_once_with(
            host="127.0.0.1", port=3306, user="root", database="x",
            connect_timeout=2, charset="utf8mb4", autocommit=False,
        )

    def test_url_invalida(self):
        for url in ("postgresql://u@h/b", "host=x dbname=y", "mysql://u@h:abc/b"):
            with self.subTest(url):
                with self.assertRaises(PersistenciaError):
                    parametros_da_url(url)

    def test_falta_de_cryptography_vira_persistencia_error(self):
        with mock.patch(
            "src.persistencia.conexao_mysql.pymysql.connect",
            side_effect=RuntimeError("'cryptography' package is required"),
        ):
            with self.assertRaises(PersistenciaError) as ctx:
                with GerenciadorConexaoMySQL("mysql://u:p@h/b"):
                    pass
        self.assertIn("cryptography", str(ctx.exception))

    def test_fechar_sem_abrir_nao_faz_nada(self):
        GerenciadorConexaoMySQL("mysql://u:p@h/b").fechar()


@apoio_mysql.requer_mysql
class TestGerenciadorComBancoReal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        apoio_mysql.preparar_banco()

    def setUp(self):
        apoio_mysql.resetar_dados()

    def contar_cnaes(self):
        return apoio_mysql.executar("SELECT COUNT(*) FROM cnae")[0][0]

    def test_commit_grava_de_verdade(self):
        antes = self.contar_cnaes()

        with apoio_mysql.gerenciador() as ger:
            with ger.cursor() as cur:
                cur.execute("INSERT INTO cnae VALUES ('9999999', 'Novo')")

        self.assertEqual(self.contar_cnaes(), antes + 1)

    def test_erro_desfaz_o_que_foi_gravado(self):
        antes = self.contar_cnaes()

        with self.assertRaises(RuntimeError):
            with apoio_mysql.gerenciador() as ger:
                with ger.cursor() as cur:
                    cur.execute("INSERT INTO cnae VALUES ('9999999', 'Novo')")
                raise RuntimeError("falhou depois do insert")

        self.assertEqual(self.contar_cnaes(), antes)

    def test_rollback_manual_descarta_so_o_que_veio_depois_do_commit(self):
        antes = self.contar_cnaes()

        with apoio_mysql.gerenciador() as ger:
            with ger.cursor() as cur:
                cur.execute("INSERT INTO cnae VALUES ('9999991', 'Fica')")
                ger.commit()
                cur.execute("INSERT INTO cnae VALUES ('9999992', 'Some')")
                ger.rollback()

        self.assertEqual(self.contar_cnaes(), antes + 1)

    def test_erro_de_sql_dentro_do_with_desfaz_tudo_e_propaga(self):
        antes = self.contar_cnaes()

        with self.assertRaises(pymysql.err.IntegrityError):
            with apoio_mysql.gerenciador() as ger:
                with ger.cursor() as cur:
                    cur.execute("INSERT INTO cnae VALUES ('9999999', 'A')")
                    cur.execute("INSERT INTO cnae VALUES ('9999999', 'B')")

        self.assertEqual(self.contar_cnaes(), antes)

    def test_conexao_fica_fechada_depois_do_with(self):
        ger = apoio_mysql.gerenciador()
        with ger:
            self.assertTrue(ger.aberta)
        self.assertFalse(ger.aberta)

    def test_servidor_recusando_conexao(self):
        ger = GerenciadorConexaoMySQL(port=1, connect_timeout=2)
        with self.assertRaises(PersistenciaError):
            with ger:
                pass

    def test_senha_errada_e_nao_aparece_na_mensagem(self):
        ger = GerenciadorConexaoMySQL(
            apoio_mysql.URL, user="usuario_que_nao_existe", password="senha-errada"
        )
        with self.assertRaises(PersistenciaError) as ctx:
            with ger:
                pass
        self.assertNotIn("senha-errada", str(ctx.exception))

    def test_banco_inexistente(self):
        ger = GerenciadorConexaoMySQL(apoio_mysql.URL, database="banco_que_nao_existe")
        with self.assertRaises(PersistenciaError):
            with ger:
                pass



if __name__ == "__main__":
    unittest.main()

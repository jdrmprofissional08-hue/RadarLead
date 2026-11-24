
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from src.integracoes.servico_importacao import ServicoImportacaoEmpresas


class TestServicoImportacaoEmpresas(unittest.TestCase):

    def setUp(self):
        self.consulta = Mock()
        self.repositorio = Mock()

        def consultar(cnpj, classe_empresa=None):
            return SimpleNamespace(cnpj=cnpj)

        self.consulta.consultar_empresa.side_effect = consultar

        self.servico = ServicoImportacaoEmpresas(
            self.consulta,
            self.repositorio
        )

    def test_importacao_de_duas_empresas(self):
        resultado = self.servico.importar_cnpjs([
            "11111111000111",
            "22222222000122"
        ])

        self.assertEqual(len(resultado["importados"]), 2)
        self.assertEqual(
            self.repositorio.salvar_empresa.call_count, 2
        )

    def test_nao_importar_cnpj_duplicado(self):
        resultado = self.servico.importar_cnpjs([
            "11.111.111/0001-11",
            "11111111000111"
        ])

        self.assertEqual(len(resultado["importados"]), 1)
        self.assertEqual(len(resultado["duplicados"]), 1)
        self.repositorio.salvar_empresa.assert_called_once()

    def test_falha_nao_interrompe_importacao(self):
        def consultar(cnpj, classe_empresa=None):
            if cnpj == "11111111000111":
                raise ConnectionError("Falha simulada")

            return SimpleNamespace(cnpj=cnpj)

        self.consulta.consultar_empresa.side_effect = consultar

        resultado = self.servico.importar_cnpjs([
            "11111111000111",
            "22222222000122"
        ])

        self.assertEqual(len(resultado["falhas"]), 1)
        self.assertEqual(len(resultado["importados"]), 1)
        self.repositorio.salvar_empresa.assert_called_once()

    def test_cnpj_invalido(self):
        resultado = self.servico.importar_cnpjs([
            "abc",
            "11111111000111"
        ])

        self.assertEqual(len(resultado["falhas"]), 1)
        self.assertEqual(len(resultado["importados"]), 1)


if __name__ == "__main__":
    unittest.main()

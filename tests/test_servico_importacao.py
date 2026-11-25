
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from src.integracoes.servico_importacao import (
    ServicoImportacaoEmpresas
)


class EmpresaNaoEncontradaSimulada(Exception):
    pass


class TestServicoImportacaoEmpresas(unittest.TestCase):

    def setUp(self):
        self.consulta = Mock()
        self.repositorio = Mock()

        # Simula os CNPJs que ja existem no banco.
        self.existentes = set()

        def buscar_empresa(cnpj):
            if cnpj not in self.existentes:
                raise EmpresaNaoEncontradaSimulada(
                    "Empresa nao encontrada"
                )
            return SimpleNamespace(cnpj=cnpj)

        self.repositorio.buscar_empresa.side_effect = (
            buscar_empresa
        )

        def consultar(cnpj, classe_empresa=None):
            return SimpleNamespace(cnpj=cnpj)

        self.consulta.consultar_empresa.side_effect = consultar

        self.servico = ServicoImportacaoEmpresas(
            self.consulta,
            self.repositorio,
            erros_empresa_nao_encontrada=(
                EmpresaNaoEncontradaSimulada,
            )
        )

    def test_importacao_de_duas_empresas(self):
        resultado = self.servico.importar_cnpjs([
            "11111111000111",
            "22222222000122"
        ])

        self.assertEqual(len(resultado["importados"]), 2)
        self.assertEqual(
            self.repositorio.salvar_empresa.call_count,
            2
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

    def test_empresa_ja_cadastrada(self):
        cnpj = "11111111000111"
        self.existentes.add(cnpj)

        resultado = self.servico.importar_cnpjs([cnpj])

        self.assertEqual(resultado["importados"], [])
        self.assertEqual(
            resultado["ja_cadastrados"],
            [cnpj]
        )

        self.consulta.consultar_empresa.assert_not_called()
        self.repositorio.salvar_empresa.assert_not_called()

    def test_importa_apenas_empresa_nova(self):
        existente = "11111111000111"
        nova = "22222222000122"

        self.existentes.add(existente)

        resultado = self.servico.importar_cnpjs([
            existente,
            nova
        ])

        self.assertEqual(
            resultado["ja_cadastrados"],
            [existente]
        )
        self.assertEqual(resultado["importados"], [nova])

        self.assertEqual(
            self.repositorio.salvar_empresa.call_count,
            1
        )

    def test_erro_de_dominio_nao_interrompe_importacao(self):
        class ErroDeDominioSimulado(Exception):
            pass

        self.servico = ServicoImportacaoEmpresas(
            self.consulta,
            self.repositorio,
            erros_dominio=(ErroDeDominioSimulado,),
            erros_empresa_nao_encontrada=(
                EmpresaNaoEncontradaSimulada,
            )
        )

        def consultar(cnpj, classe_empresa=None):
            if cnpj == "22222222000122":
                raise ErroDeDominioSimulado(
                    "Dados empresariais invalidos"
                )

            return SimpleNamespace(cnpj=cnpj)

        self.consulta.consultar_empresa.side_effect = consultar

        resultado = self.servico.importar_cnpjs([
            "11111111000111",
            "22222222000122",
            "33333333000133"
        ])

        self.assertEqual(
            resultado["importados"],
            ["11111111000111", "33333333000133"]
        )
        self.assertEqual(len(resultado["falhas"]), 1)
        self.assertEqual(
            self.repositorio.salvar_empresa.call_count,
            2
        )

    def test_verifica_existente_sem_listar_todas(self):
        cnpj = "11111111000111"
        self.existentes.add(cnpj)

        # Se o importador tentar carregar tudo, o teste falha.
        self.repositorio.listar_empresas.side_effect = (
            AssertionError("Nao deve listar todas as empresas")
        )

        resultado = self.servico.importar_cnpjs([cnpj])

        self.assertEqual(
            resultado["ja_cadastrados"],
            [cnpj]
        )
        self.repositorio.buscar_empresa.assert_called_once_with(
            cnpj
        )
        self.repositorio.listar_empresas.assert_not_called()
        self.consulta.consultar_empresa.assert_not_called()


if __name__ == "__main__":
    unittest.main()

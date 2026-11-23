
import unittest
from unittest.mock import Mock

from src.integracoes.servico_empresa import ServicoConsultaEmpresa


class TestServicoConsultaEmpresa(unittest.TestCase):

    def setUp(self):
        self.cliente = Mock()

        self.dados_cnpj = {
            "cnpj": "19131243000197",
            "razao_social": "Empresa Teste",
            "cnae_fiscal": 6204000,
            "codigo_porte": 3,
            "codigo_municipio_ibge": 5205109,
            "situacao_cadastral": 2,
            "cep": "75701000"
        }

        self.dados_cep = {
            "cep": "75701000",
            "city": "Catalao",
            "state": "GO",
            "ibge": {"city": "5205109"},
            "location": {
                "coordinates": {
                    "latitude": -18.16,
                    "longitude": -47.94
                }
            }
        }

        self.cliente.consultar_cnpj.return_value = self.dados_cnpj
        self.cliente.consultar_cep.return_value = self.dados_cep

        self.servico = ServicoConsultaEmpresa(
            cliente=self.cliente
        )

    def test_empresa_completa(self):
        empresa = self.servico.consultar_dados(
            "19131243000197"
        )

        self.assertEqual(empresa["cnpj"], "19131243000197")
        self.assertEqual(empresa["cnae_principal"], "6204000")
        self.assertEqual(empresa["situacao_cadastral"], 2)
        self.assertEqual(empresa["latitude"], -18.16)
        self.assertEqual(empresa["longitude"], -47.94)

        self.cliente.consultar_cep.assert_called_once_with(
            "75701000"
        )

    def test_empresa_sem_cep(self):
        self.dados_cnpj["cep"] = None

        with self.assertRaises(ValueError):
            self.servico.consultar_dados("19131243000197")

        self.cliente.consultar_cep.assert_not_called()

    def test_cep_divergente(self):
        self.dados_cep["cep"] = "74000000"

        with self.assertRaises(ValueError):
            self.servico.consultar_dados("19131243000197")

    def test_municipio_divergente(self):
        self.dados_cep["ibge"]["city"] = "5208707"

        with self.assertRaises(ValueError):
            self.servico.consultar_dados("19131243000197")


if __name__ == "__main__":
    unittest.main()

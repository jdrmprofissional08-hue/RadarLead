
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


    def test_conversao_para_objeto_empresa(self):
        classe_simulada = Mock()
        objeto_esperado = object()

        classe_simulada.from_dict.return_value = objeto_esperado

        resultado = self.servico.consultar_empresa(
            "19131243000197",
            classe_empresa=classe_simulada
        )

        self.assertIs(resultado, objeto_esperado)

        classe_simulada.from_dict.assert_called_once()

        dados_recebidos = (
            classe_simulada.from_dict.call_args.args[0]
        )

        self.assertEqual(
            dados_recebidos["situacao_cadastral"], 2
        )
        self.assertEqual(
            dados_recebidos["latitude"], -18.16
        )

    def test_cnpj_retorno_divergente(self):
        # Simula a API retornando outro CNPJ.
        self.dados_cnpj["cnpj"] = "99999999000199"

        # O servico deve rejeitar a divergencia.
        with self.assertRaises(ValueError):
            self.servico.consultar_dados("19131243000197")


if __name__ == "__main__":
    unittest.main()

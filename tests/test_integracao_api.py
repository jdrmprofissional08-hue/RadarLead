
import json
import unittest
from io import BytesIO
from unittest.mock import patch

from src.integracoes.brasilapi import ClienteBrasilAPI
from src.integracoes.normalizador import Normalizador


class TestIntegracaoAPI(unittest.TestCase):

    def test_consulta_e_normalizacao_cnpj(self):
        dados_ficticios = {
            "cnpj": "19.131.243/0001-97",
            "razao_social": "Empresa Exemplo LTDA",
            "cnae_fiscal": 6204000,
            "codigo_porte": 3,
            "codigo_municipio_ibge": 5205109,
            "cnaes_secundarios": [
                {"codigo": 6201501}
            ],
            "cep": "75701000"
        }

        resposta = BytesIO(
            json.dumps(dados_ficticios).encode("utf-8")
        )

        cliente = ClienteBrasilAPI()
        normalizador = Normalizador()

        with patch(
            "src.integracoes.brasilapi.urlopen",
            return_value=resposta
        ):
            dados = cliente.consultar_cnpj(
                "19.131.243/0001-97"
            )

        empresa = normalizador.normalizar_cnpj(dados)

        self.assertEqual(empresa["cnae_principal"], "6204000")
        self.assertEqual(empresa["porte"], 3)
        self.assertEqual(empresa["municipio_ibge"], "5205109")
        self.assertEqual(
            empresa["cnaes_secundarios"], ["6201501"]
        )
        self.assertEqual(empresa["cep"], "75701000")

    def test_consulta_e_normalizacao_cep(self):
        dados_ficticios = {
            "cep": "75701-000",
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

        resposta = BytesIO(
            json.dumps(dados_ficticios).encode("utf-8")
        )

        cliente = ClienteBrasilAPI()
        normalizador = Normalizador()

        with patch(
            "src.integracoes.brasilapi.urlopen",
            return_value=resposta
        ):
            dados = cliente.consultar_cep("75701-000")

        endereco = normalizador.normalizar_cep(dados)

        self.assertEqual(endereco["cep"], "75701000")
        self.assertEqual(endereco["municipio_ibge"], "5205109")
        self.assertEqual(endereco["latitude"], -18.16)
        self.assertEqual(endereco["longitude"], -47.94)


    def test_contrato_empresa_backend(self):
        dados_api = {
            "cnpj": "19131243000197",
            "razao_social": "Empresa Exemplo LTDA",
            "cnae_fiscal": 6204000,
            "codigo_porte": 3,
            "codigo_municipio_ibge": 5205109,
            "cnaes_secundarios": [
                {"codigo": 6201501}
            ],
            "cep": "75701000"
        }

        normalizador = Normalizador()
        empresa = normalizador.normalizar_cnpj(dados_api)

        campos_esperados = {
            "cnpj",
            "razao_social",
            "cnae_principal",
            "porte",
            "municipio_ibge",
            "cnaes_secundarios",
            "cep",
            "latitude",
            "longitude",
            "situacao_cadastral",
            "natureza_juridica",
            "capital_social",
            "data_inicio_atividade",
            "data_situacao"
        }

        self.assertEqual(set(empresa.keys()), campos_esperados)
        self.assertIsInstance(empresa["cnpj"], str)
        self.assertIsInstance(empresa["porte"], int)
        self.assertIsInstance(empresa["cnae_principal"], str)
        self.assertIsInstance(empresa["municipio_ibge"], str)
        self.assertIsInstance(empresa["cnaes_secundarios"], list)
        self.assertIsNone(empresa["latitude"])
        self.assertIsNone(empresa["longitude"])


if __name__ == "__main__":
    unittest.main()

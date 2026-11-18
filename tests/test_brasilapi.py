
import json
import unittest
from io import BytesIO
from unittest.mock import patch

from src.integracoes.brasilapi import ClienteBrasilAPI

from urllib.error import HTTPError, URLError

class TestClienteBrasilAPI(unittest.TestCase):

    def test_consultar_cnpj(self):
        empresa_ficticia = {
            "cnpj": "19131243000197",
            "razao_social": "Empresa Teste",
            "cnae_fiscal": 6204000
        }

        resposta = BytesIO(
            json.dumps(empresa_ficticia).encode("utf-8")
        )

        with patch(
            "src.integracoes.brasilapi.urlopen",
            return_value=resposta
        ) as consulta_falsa:

            cliente = ClienteBrasilAPI()
            resultado = cliente.consultar_cnpj("19.131.243/0001-97")

        self.assertEqual(resultado, empresa_ficticia)
        consulta_falsa.assert_called_once()

    def test_cnpj_invalido(self):
        cliente = ClienteBrasilAPI()

        with self.assertRaises(ValueError):
            cliente.consultar_cnpj("123")


    def test_consultar_cep(self):
        cep_ficticio = {
            "cep": "75701000",
            "city": "Catalao",
            "state": "GO"
        }

        resposta = BytesIO(
            json.dumps(cep_ficticio).encode("utf-8")
        )

        with patch(
            "src.integracoes.brasilapi.urlopen",
            return_value=resposta
        ):
            cliente = ClienteBrasilAPI()
            resultado = cliente.consultar_cep("75701-000")

        self.assertEqual(resultado, cep_ficticio)

    def test_cep_invalido(self):
        cliente = ClienteBrasilAPI()

        with self.assertRaises(ValueError):
            cliente.consultar_cep("123")


    def test_cnpj_nao_encontrado(self):
        erro = HTTPError(
            "https://brasilapi.com.br",
            404,
            "Not Found",
            {},
            None
        )

        with patch(
            "src.integracoes.brasilapi.urlopen",
            side_effect=erro
        ):
            cliente = ClienteBrasilAPI()

            with self.assertRaises(ValueError):
                cliente.consultar_cnpj("19131243000197")

    def test_cep_nao_encontrado(self):
        erro = HTTPError(
            "https://brasilapi.com.br",
            404,
            "Not Found",
            {},
            None
        )

        with patch(
            "src.integracoes.brasilapi.urlopen",
            side_effect=erro
        ):
            cliente = ClienteBrasilAPI()

            with self.assertRaises(ValueError):
                cliente.consultar_cep("75701000")

    def test_falha_de_conexao(self):
        with patch(
            "src.integracoes.brasilapi.urlopen",
            side_effect=URLError("Sem conexao")
        ):
            cliente = ClienteBrasilAPI()

            with self.assertRaises(ConnectionError):
                cliente.consultar_cnpj("19131243000197")

    def test_json_invalido(self):
        resposta = BytesIO(b"{json invalido")

        with patch(
            "src.integracoes.brasilapi.urlopen",
            return_value=resposta
        ):
            cliente = ClienteBrasilAPI()

            with self.assertRaises(ValueError):
                cliente.consultar_cnpj("19131243000197")


if __name__ == "__main__":
    unittest.main()

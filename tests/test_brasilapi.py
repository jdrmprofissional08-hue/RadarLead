
import json
import unittest
from io import BytesIO
from unittest.mock import patch
from threading import Barrier

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
        self.addCleanup(erro.close)

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


    def test_consultas_paralelas(self):
        cnpjs = [
            "11111111000191",
            "22222222000191",
            "33333333000191"
        ]

        barreira = Barrier(3)

        def consulta_simulada(cnpj):
            barreira.wait(timeout=5)
            return {
                "cnpj": cnpj,
                "razao_social": "Empresa Teste"
            }

        cliente = ClienteBrasilAPI()

        with patch.object(
            cliente,
            "consultar_cnpj",
            side_effect=consulta_simulada
        ):
            resultados = cliente.consultar_cnpjs(
                cnpjs, max_workers=3
            )

        self.assertEqual(len(resultados), 3)
        self.assertTrue(all(r["sucesso"] for r in resultados))
        self.assertEqual(
            [r["cnpj"] for r in resultados], cnpjs
        )

    def test_consultas_paralelas_com_falha(self):
        cnpjs = [
            "11111111000191",
            "22222222000191",
            "33333333000191"
        ]

        def consulta_simulada(cnpj):
            if cnpj == "22222222000191":
                raise ConnectionError("Falha simulada")
            return {"cnpj": cnpj}

        cliente = ClienteBrasilAPI()

        with patch.object(
            cliente,
            "consultar_cnpj",
            side_effect=consulta_simulada
        ):
            resultados = cliente.consultar_cnpjs(
                cnpjs, max_workers=3
            )

        self.assertTrue(resultados[0]["sucesso"])
        self.assertFalse(resultados[1]["sucesso"])
        self.assertTrue(resultados[2]["sucesso"])
        self.assertIn("Falha simulada", resultados[1]["erro"])

    def test_lista_cnpjs_invalida(self):
        cliente = ClienteBrasilAPI()

        with self.assertRaises(ValueError):
            cliente.consultar_cnpjs("nao e uma lista")

    def test_numero_threads_invalido(self):
        cliente = ClienteBrasilAPI()

        with self.assertRaises(ValueError):
            cliente.consultar_cnpjs(
                ["11111111000191"], max_workers=0
            )


if __name__ == "__main__":
    unittest.main()

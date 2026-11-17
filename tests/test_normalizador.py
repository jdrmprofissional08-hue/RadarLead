
import unittest
from src.integracoes.normalizador import Normalizador


class TestNormalizador(unittest.TestCase):

    def setUp(self):
        self.normalizador = Normalizador()
        self.dados = {
            "cnpj": "19.131.243/0001-97",
            "razao_social": " Empresa Exemplo ",
            "cnae_fiscal": 6204000,
            "codigo_porte": 3,
            "codigo_municipio_ibge": 5208707
        }

    def test_normalizar_dados_validos(self):
        resultado = self.normalizador.normalizar_cnpj(self.dados)

        self.assertEqual(resultado["cnpj"], "19131243000197")
        self.assertEqual(resultado["razao_social"], "Empresa Exemplo")
        self.assertEqual(resultado["cnae_principal"], "6204000")
        self.assertEqual(resultado["porte"], 3)
        self.assertEqual(resultado["municipio_ibge"], "5208707")

    def test_cnpj_ausente(self):
        self.dados["cnpj"] = None

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cnpj(self.dados)

    def test_cnpj_invalido(self):
        self.dados["cnpj"] = "123"

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cnpj(self.dados)

    def test_razao_social_vazia(self):
        self.dados["razao_social"] = ""

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cnpj(self.dados)

    def test_cnae_invalido(self):
        self.dados["cnae_fiscal"] = "abc"

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cnpj(self.dados)

    def test_porte_invalido(self):
        self.dados["codigo_porte"] = "errado"

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cnpj(self.dados)

    def test_municipio_ausente(self):
        self.dados["codigo_municipio_ibge"] = None

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cnpj(self.dados)


if __name__ == "__main__":
    unittest.main()

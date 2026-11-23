
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


    def test_cnaes_secundarios(self):
        cnaes = [
            {"codigo": 6201501},
            {"codigo": "6311900"},
            {"codigo": 6201501}
        ]

        resultado = self.normalizador.normalizar_cnaes_secundarios(cnaes)
        self.assertEqual(resultado, ["6201501", "6311900"])

    def test_cnaes_secundarios_ausentes(self):
        resultado = self.normalizador.normalizar_cnaes_secundarios(None)
        self.assertEqual(resultado, [])

    def test_cnaes_secundarios_invalidos(self):
        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cnaes_secundarios(
                [{"codigo": "abc"}]
            )

    def test_cep_valido(self):
        dados = {
            "cep": "75701-000",
            "city": "Catalao",
            "state": "GO",
            "ibge": {"city": "5205109"}
        }

        resultado = self.normalizador.normalizar_cep(dados)

        self.assertEqual(resultado["cep"], "75701000")
        self.assertEqual(resultado["municipio"], "Catalao")
        self.assertEqual(resultado["uf"], "GO")
        self.assertEqual(resultado["municipio_ibge"], "5205109")

    def test_cep_com_coordenadas(self):
        dados = {
            "cep": "75701000",
            "city": "Catalao",
            "state": "GO",
            "location": {
                "coordinates": {
                    "latitude": -18.16,
                    "longitude": -47.94
                }
            }
        }

        resultado = self.normalizador.normalizar_cep(dados)

        self.assertEqual(resultado["latitude"], -18.16)
        self.assertEqual(resultado["longitude"], -47.94)

    def test_cep_sem_coordenadas(self):
        dados = {
            "cep": "75701000",
            "city": "Catalao",
            "state": "GO"
        }

        resultado = self.normalizador.normalizar_cep(dados)

        self.assertIsNone(resultado["latitude"])
        self.assertIsNone(resultado["longitude"])

    def test_cep_invalido(self):
        dados = {
            "cep": "123",
            "city": "Catalao",
            "state": "GO"
        }

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cep(dados)

    def test_cep_sem_municipio(self):
        dados = {
            "cep": "75701000",
            "city": None,
            "state": "GO"
        }

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cep(dados)


    def test_cep_latitude_invalida(self):
        dados = {
            "cep": "75701000",
            "city": "Catalao",
            "state": "GO",
            "location": {
                "coordinates": {
                    "latitude": 200,
                    "longitude": -47.94
                }
            }
        }

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cep(dados)

    def test_cep_coordenadas_invalidas(self):
        dados = {
            "cep": "75701000",
            "city": "Catalao",
            "state": "GO",
            "location": {
                "coordinates": "invalido"
            }
        }

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cep(dados)


    def test_latitude_nan(self):
        dados = {
            "cep": "75701000",
            "city": "Catalao",
            "state": "GO",
            "location": {
                "coordinates": {
                    "latitude": "nan",
                    "longitude": -47.94
                }
            }
        }

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cep(dados)

    def test_longitude_infinita(self):
        dados = {
            "cep": "75701000",
            "city": "Catalao",
            "state": "GO",
            "location": {
                "coordinates": {
                    "latitude": -18.16,
                    "longitude": "inf"
                }
            }
        }

        with self.assertRaises(ValueError):
            self.normalizador.normalizar_cep(dados)


    def test_situacao_cadastral_ativa(self):
        dados = {
            **self.dados,
            "situacao_cadastral": "02"
        }

        resultado = self.normalizador.normalizar_cnpj(dados)

        self.assertEqual(resultado["situacao_cadastral"], 2)

    def test_situacao_cadastral_ausente(self):
        resultado = self.normalizador.normalizar_cnpj(
            self.dados
        )

        self.assertIsNone(resultado["situacao_cadastral"])

    def test_situacao_cadastral_invalida(self):
        for valor in ["ATIVA", 0, True, -1]:
            with self.subTest(valor=valor):
                dados = {
                    **self.dados,
                    "situacao_cadastral": valor
                }

                with self.assertRaises(ValueError):
                    self.normalizador.normalizar_cnpj(dados)


    def test_dados_cadastrais_completos(self):
        dados = {
            **self.dados,
            "codigo_natureza_juridica": 2062,
            "capital_social": 150000.50,
            "data_inicio_atividade": "2020-05-10",
            "data_situacao_cadastral": "2024-02-15"
        }

        resultado = self.normalizador.normalizar_cnpj(dados)

        self.assertEqual(resultado["natureza_juridica"], "2062")
        self.assertEqual(resultado["capital_social"], 150000.50)
        self.assertEqual(
            resultado["data_inicio_atividade"], "2020-05-10"
        )
        self.assertEqual(
            resultado["data_situacao"], "2024-02-15"
        )

    def test_dados_cadastrais_ausentes(self):
        resultado = self.normalizador.normalizar_cnpj(
            self.dados
        )

        self.assertIsNone(resultado["natureza_juridica"])
        self.assertIsNone(resultado["capital_social"])
        self.assertIsNone(resultado["data_inicio_atividade"])
        self.assertIsNone(resultado["data_situacao"])

    def test_dados_cadastrais_invalidos(self):
        casos = [
            ("codigo_natureza_juridica", True),
            ("capital_social", -100),
            ("data_inicio_atividade", "2024-02-30"),
            ("data_situacao_cadastral", "data errada")
        ]

        for campo, valor in casos:
            with self.subTest(campo=campo):
                dados = {**self.dados, campo: valor}

                with self.assertRaises(ValueError):
                    self.normalizador.normalizar_cnpj(dados)


if __name__ == "__main__":
    unittest.main()
 
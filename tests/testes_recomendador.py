
import unittest

from src.Recomendadores.base import Recomendador
from src.Recomendadores.classificador import ClassificadorPorConteudo


class TestRecomendador(unittest.TestCase):

    def setUp(self):
        self.classificador = ClassificadorPorConteudo()

        self.perfil = {
            "cnaes_desejados": ["5611201"],
            "porte_desejado": 3,
            "municipio_alvo_ibge": "5208707"
        }

        self.empresas = [
            {
                "cnpj": "11111111000111",
                "razao_social": "Restaurante A",
                "cnae_principal": "5611201",
                "porte": 3,
                "municipio_ibge": "5208707"
            },
            {
                "cnpj": "22222222000122",
                "razao_social": "Restaurante B",
                "cnae_principal": "5611201",
                "porte": 5,
                "municipio_ibge": "5208707"
            },
            {
                "cnpj": "33333333000133",
                "razao_social": "Empresa C",
                "cnae_principal": "4520001",
                "porte": 5,
                "municipio_ibge": "3550308"
            }
        ]

    def test_heranca(self):
        self.assertIsInstance(
            self.classificador, Recomendador
        )

    def test_pontuacao_maxima(self):
        resultado = self.classificador.classificar(
            self.empresas[0], self.perfil
        )
        self.assertEqual(resultado["pontuacao"], 100)

    def test_pontuacao_parcial(self):
        resultado = self.classificador.classificar(
            self.empresas[1], self.perfil
        )
        self.assertEqual(resultado["pontuacao"], 75)

    def test_ordenacao(self):
        resultados = self.classificador.recomendar(
            self.empresas, self.perfil
        )

        self.assertEqual(
            [item["pontuacao"] for item in resultados],
            [100, 75, 0]
        )

    def test_lista_vazia(self):
        resultados = self.classificador.recomendar(
            [], self.perfil
        )
        self.assertEqual(resultados, [])

    def test_interface_abstrata(self):
        with self.assertRaises(TypeError):
            Recomendador()


if __name__ == "__main__":
    unittest.main()

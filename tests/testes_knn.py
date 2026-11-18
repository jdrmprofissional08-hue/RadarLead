
import unittest

from src.Recomendadores.base import Recomendador
from src.Recomendadores.similaridade import RecomendadorKNN


def empresa(cnpj, cnae="5611201", porte=3,
            municipio="5208707", **extra):

    return {
        "cnpj": cnpj,
        "razao_social": "Empresa fictícia",
        "cnae_principal": cnae,
        "porte": porte,
        "municipio_ibge": municipio,
        **extra
    }


class TestKNN(unittest.TestCase):

    def setUp(self):
        self.perfil = {
            "peso_cnae": 50,
            "peso_porte": 25,
            "peso_localizacao": 25
        }

        self.historico = [
            empresa(
                "11111111000111",
                converteu=True
            ),
            empresa(
                "22222222000122",
                porte=5,
                converteu=True
            ),
            empresa(
                "33333333000133",
                cnae="4520001",
                municipio="3550308",
                converteu=False
            )
        ]

        self.knn = RecomendadorKNN(
            self.historico,
            k=2
        )

    def test_heranca(self):
        self.assertIsInstance(self.knn, Recomendador)

    def test_pontuacao(self):
        resultado = self.knn.recomendar(
            [empresa("44444444000144")],
            self.perfil
        )

        self.assertEqual(resultado[0]["pontuacao"], 100)

    def test_lista_vazia(self):
        self.assertEqual(
            self.knn.recomendar([], self.perfil),
            []
        )

    def test_ordenacao(self):
        resultado = self.knn.recomendar(
            [
                empresa("44444444000144"),
                empresa(
                    "55555555000155",
                    cnae="4520001",
                    municipio="3550308"
                )
            ],
            self.perfil
        )

        self.assertGreaterEqual(
            resultado[0]["pontuacao"],
            resultado[1]["pontuacao"]
        )

    def test_historico_vazio(self):
        with self.assertRaisesRegex(ValueError, "histórico"):
            RecomendadorKNN().recomendar(
                [empresa("44444444000144")],
                self.perfil
            )

    def test_k_invalido(self):
        with self.assertRaises(ValueError):
            RecomendadorKNN(k=0)

    def test_rotulo_ausente(self):
        with self.assertRaises(ValueError):
            RecomendadorKNN([
                empresa("11111111000111")
            ])

    def test_pesos(self):
        with self.assertRaises(ValueError):
            self.knn.recomendar(
                [empresa("44444444000144")],
                {
                    "peso_cnae": 25,
                    "peso_porte": 25,
                    "peso_localizacao": 25
                }
            )

    def test_excluir_mesmo_cnpj(self):
        knn = RecomendadorKNN(
            [
                empresa(
                    "11111111000111",
                    converteu=True
                ),
                empresa(
                    "22222222000122",
                    converteu=False
                )
            ],
            k=1
        )

        resultado = knn.recomendar(
            [empresa("11111111000111")],
            self.perfil
        )

        self.assertEqual(resultado[0]["pontuacao"], 0)

    def test_sem_vizinhos(self):
        knn = RecomendadorKNN([
            empresa(
                "11111111000111",
                converteu=True
            )
        ])

        with self.assertRaisesRegex(ValueError, "independentes"):
            knn.recomendar(
                [empresa("11111111000111")],
                self.perfil
            )

    def test_cnae_desconhecido(self):
        resultado = self.knn.recomendar(
            [
                empresa(
                    "44444444000144",
                    cnae="9999999"
                )
            ],
            self.perfil
        )

        self.assertEqual(len(resultado), 1)

    def test_historico_duplicado(self):
        with self.assertRaises(ValueError):
            RecomendadorKNN([
                self.historico[0],
                self.historico[0]
            ])


if __name__ == "__main__":
    unittest.main()

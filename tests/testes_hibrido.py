
import unittest

from src.Recomendadores.base import Recomendador
from src.Recomendadores.hibrido import RecomendadorHibrido


def empresa(cnpj, cnae="5611201", porte=3,
            municipio="5208707", **extra):
    return {
        "cnpj": cnpj,
        "razao_social": "Empresa Exemplo",
        "cnae_principal": cnae,
        "porte": porte,
        "municipio_ibge": municipio,
        **extra
    }


class TestRecomendadorHibrido(unittest.TestCase):

    def setUp(self):
        self.perfil = {
            "cnaes_desejados": ["5611201"],
            "porte_desejado": 3,
            "municipio_alvo_ibge": "5208707",
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
                converteu=False
            )
        ]

        self.candidata = empresa("33333333000133")

    def test_heranca(self):
        hibrido = RecomendadorHibrido()
        self.assertIsInstance(hibrido, Recomendador)

    def test_pontuacao_hibrida(self):
        hibrido = RecomendadorHibrido(
            historico=self.historico,
            k=2
        )

        resultado = hibrido.recomendar(
            [self.candidata], self.perfil
        )

        self.assertEqual(resultado[0]["pontuacao"], 85)
        self.assertEqual(
            resultado[0]["pontuacao_conteudo"], 100
        )
        self.assertEqual(
            resultado[0]["pontuacao_knn"], 50
        )

    def test_sem_historico(self):
        hibrido = RecomendadorHibrido()

        resultado = hibrido.recomendar(
            [self.candidata], self.perfil
        )

        self.assertEqual(resultado[0]["pontuacao"], 100)
        self.assertIsNone(resultado[0]["pontuacao_knn"])

    def test_pesos_personalizados(self):
        perfil = dict(self.perfil)
        perfil["peso_cnae"] = 60
        perfil["peso_porte"] = 20
        perfil["peso_localizacao"] = 20

        hibrido = RecomendadorHibrido()

        candidata = empresa(
            "33333333000133",
            porte=5
        )

        resultado = hibrido.recomendar(
            [candidata], perfil
        )

        self.assertEqual(resultado[0]["pontuacao"], 80)

    def test_peso_hibrido_personalizado(self):
        hibrido = RecomendadorHibrido(
            historico=self.historico,
            k=2,
            peso_conteudo=0.5
        )

        resultado = hibrido.recomendar(
            [self.candidata], self.perfil
        )

        self.assertEqual(resultado[0]["pontuacao"], 75)

    def test_lista_vazia(self):
        hibrido = RecomendadorHibrido()

        resultado = hibrido.recomendar([], self.perfil)

        self.assertEqual(resultado, [])

    def test_ordenacao(self):
        hibrido = RecomendadorHibrido()

        candidatas = [
            empresa(
                "33333333000133",
                cnae="4520001",
                porte=5,
                municipio="3550308"
            ),
            empresa("44444444000144")
        ]

        resultado = hibrido.recomendar(
            candidatas, self.perfil
        )

        self.assertEqual(
            resultado[0]["cnpj"],
            "44444444000144"
        )

    def test_pesos_invalidos(self):
        perfil = dict(self.perfil)
        perfil["peso_cnae"] = 20

        hibrido = RecomendadorHibrido()

        with self.assertRaises(ValueError):
            hibrido.recomendar(
                [self.candidata], perfil
            )

    def test_parametro_invalido(self):
        with self.assertRaises(ValueError):
            RecomendadorHibrido(peso_conteudo=1.5)

    def test_treinamento_posterior(self):
        hibrido = RecomendadorHibrido(k=2)

        hibrido.treinar(self.historico)

        resultado = hibrido.recomendar(
            [self.candidata], self.perfil
        )

        self.assertEqual(resultado[0]["pontuacao"], 85)


if __name__ == "__main__":
    unittest.main()

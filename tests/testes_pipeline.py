
import unittest
from copy import deepcopy

from src.Recomendadores.base import Recomendador
from src.Recomendadores.classificador import ClassificadorPorConteudo
from src.Recomendadores.filtro_elegibilidade import FiltroElegibilidade
from src.Recomendadores.pipeline import RecomendadorComFiltro


class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.filtro = FiltroElegibilidade(
            cnaes_diretos=["5611201"],
            cnaes_relacionados=["5611203"],
            raio_max_km=350
        )

        self.classificador = ClassificadorPorConteudo()

        self.pipeline = RecomendadorComFiltro(
            recomendador=self.classificador,
            filtro=self.filtro,
            fornecedor={
                "latitude": -16.6869,
                "longitude": -49.2648
            }
        )

        self.perfil = {
            "cnaes_desejados": ["5611201"],
            "porte_desejado": 3,
            "municipio_alvo_ibge": "5208707",
            "peso_cnae": 50,
            "peso_porte": 25,
            "peso_localizacao": 25
        }

        self.empresa = {
            "cnpj": "11111111000111",
            "razao_social": "Restaurante A",
            "situacao_cadastral": 2,
            "cnae_principal": "5611201",
            "cnaes_secundarios": [],
            "porte": 3,
            "municipio_ibge": "5208707",
            "cep": "74000000",
            "latitude": -16.70,
            "longitude": -49.30
        }

    def test_heranca(self):
        self.assertIsInstance(
            self.pipeline, Recomendador
        )

    def test_empresa_aprovada(self):
        resultado = self.pipeline.recomendar(
            [self.empresa], self.perfil
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["pontuacao"], 100)
        self.assertIn("distancia_km", resultado[0])

    def test_empresa_inativa(self):
        empresa = deepcopy(self.empresa)
        empresa["situacao_cadastral"] = 8

        resultado = self.pipeline.recomendar(
            [empresa], self.perfil
        )

        self.assertEqual(resultado, [])
        self.assertEqual(len(self.pipeline.eliminadas), 1)

    def test_cnae_incompativel(self):
        empresa = deepcopy(self.empresa)
        empresa["cnae_principal"] = "4520001"

        resultado = self.pipeline.recomendar(
            [empresa], self.perfil
        )

        self.assertEqual(resultado, [])

    def test_sem_geolocalizacao(self):
        empresa = deepcopy(self.empresa)
        empresa["latitude"] = None

        resultado = self.pipeline.recomendar(
            [empresa], self.perfil
        )

        self.assertEqual(resultado, [])
        self.assertIn(
            "Geolocalização",
            self.pipeline.eliminadas[0]["motivo"]
        )

    def test_distancia_acima_limite(self):
        empresa = deepcopy(self.empresa)
        empresa["latitude"] = -23.55
        empresa["longitude"] = -46.63

        resultado = self.pipeline.recomendar(
            [empresa], self.perfil
        )

        self.assertEqual(resultado, [])

    def test_cnae_relacionado(self):
        empresa = deepcopy(self.empresa)
        empresa["cnae_principal"] = "5611203"

        resultado = self.pipeline.recomendar(
            [empresa], self.perfil
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(
            resultado[0]["compatibilidade"],
            "relacionada"
        )

    def test_duplicidade(self):
        resultado = self.pipeline.recomendar(
            [self.empresa, deepcopy(self.empresa)],
            self.perfil
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(len(self.pipeline.eliminadas), 1)

    def test_lista_vazia(self):
        resultado = self.pipeline.recomendar(
            [], self.perfil
        )

        self.assertEqual(resultado, [])
        self.assertEqual(self.pipeline.total_avaliadas, 0)

    def test_retorno_backend(self):
        resultado = self.pipeline.recomendar(
            [self.empresa], self.perfil
        )

        lead = resultado[0]

        self.assertIn("cnpj", lead)
        self.assertIn("razao_social", lead)
        self.assertIn("pontuacao", lead)
        self.assertIn("justificativas", lead)

    def test_situacao_ausente(self):
        empresa = deepcopy(self.empresa)
        del empresa["situacao_cadastral"]

        resultado = self.pipeline.recomendar(
            [empresa], self.perfil
        )

        self.assertEqual(resultado, [])

    def test_fornecedor_sem_coordenadas(self):
        pipeline = RecomendadorComFiltro(
            self.classificador,
            self.filtro,
            fornecedor={}
        )

        with self.assertRaises(ValueError):
            pipeline.recomendar(
                [self.empresa], self.perfil
            )


if __name__ == "__main__":
    unittest.main()


import unittest
from copy import deepcopy

from src.Recomendadores.filtro_elegibilidade import FiltroElegibilidade


class TestFiltroElegibilidade(unittest.TestCase):

    def setUp(self):
        self.filtro = FiltroElegibilidade(
            cnaes_diretos=["5611201"],
            cnaes_relacionados=["5611203", "5620101"],
            raio_max_km=350
        )

        self.cnpj = {
            "cnpj": "12345678000190",
            "situacao_cadastral": 2,
            "cnae_fiscal": 5611201,
            "cnaes_secundarios": [],
            "cep": "74000000"
        }

        self.cep = {
            "cep": "74000000",
            "location": {
                "coordinates": {
                    "latitude": "-16.70",
                    "longitude": "-49.30"
                }
            }
        }

        self.fornecedor = {
            "latitude": -16.6869,
            "longitude": -49.2648
        }

    def testar(self, alteracoes_cnpj=None,
               alteracoes_cep=None, fornecedor=None):

        cnpj = deepcopy(self.cnpj)
        cep = deepcopy(self.cep)

        if alteracoes_cnpj:
            cnpj.update(alteracoes_cnpj)

        if alteracoes_cep:
            cep.update(alteracoes_cep)

        return self.filtro.avaliar(
            cnpj,
            cep,
            fornecedor if fornecedor is not None else self.fornecedor
        )

    def test_empresa_compativel(self):
        resultado = self.testar()

        self.assertTrue(resultado["aprovada"])
        self.assertEqual(resultado["compatibilidade"], "direta")
        self.assertEqual(resultado["fator_atividade"], 1.0)

    def test_empresa_inativa(self):
        resultado = self.testar(
            alteracoes_cnpj={"situacao_cadastral": 8}
        )
        self.assertFalse(resultado["aprovada"])

    def test_ramo_relacionado(self):
        resultado = self.testar(
            alteracoes_cnpj={"cnae_fiscal": 5611203}
        )
        self.assertTrue(resultado["aprovada"])
        self.assertEqual(resultado["fator_atividade"], 0.6)

    def test_ramo_incompativel(self):
        resultado = self.testar(
            alteracoes_cnpj={"cnae_fiscal": 4520001}
        )
        self.assertFalse(resultado["aprovada"])

    def test_sem_geolocalizacao(self):
        resultado = self.testar(
            alteracoes_cep={"location": None}
        )
        self.assertFalse(resultado["aprovada"])

    def test_distancia_muito_grande(self):
        resultado = self.testar(
            alteracoes_cep={
                "location": {
                    "coordinates": {
                        "latitude": -23.55,
                        "longitude": -46.63
                    }
                }
            }
        )
        self.assertFalse(resultado["aprovada"])

    def test_cep_diferente(self):
        resultado = self.testar(
            alteracoes_cep={"cep": "89010025"}
        )
        self.assertFalse(resultado["aprovada"])


if __name__ == "__main__":
    unittest.main()

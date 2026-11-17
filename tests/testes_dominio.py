import unittest

from src.dominio.empresa import Empresa
from src.dominio.lead import Lead, StatusLead
from src.dominio.perfil import Perfil
from src.excecoes import (
    DadosInvalidosError,
    EmpresaInvalidaError,
    PerfilInvalidoError,
)


def empresa_valida(**alteracoes):
    dados = {
        "cnpj": "11111111000111",
        "razao_social": "Restaurante A",
        "cnae_principal": "5611201",
        "porte": 3,
        "municipio_ibge": "5208707",
    }
    dados.update(alteracoes)
    return Empresa(**dados)


def perfil_valido(**alteracoes):
    dados = {
        "nome": "Software em Catalão",
        "cnaes_desejados": ["6204000"],
        "porte_desejado": 3,
        "municipio_alvo_ibge": "5208707",
    }
    dados.update(alteracoes)
    return Perfil(**dados)


class TestEmpresa(unittest.TestCase):

    def test_normaliza_cnpj_com_pontuacao(self):
        empresa = empresa_valida(cnpj="11.111.111/0001-11")
        self.assertEqual(empresa.cnpj, "11111111000111")

    def test_normaliza_cnae_e_ibge_inteiros(self):
        empresa = empresa_valida(cnae_principal=561201, municipio_ibge=5208707)
        self.assertEqual(empresa.cnae_principal, "0561201")
        self.assertEqual(empresa.municipio_ibge, "5208707")

    def test_normaliza_cnaes_secundarios(self):
        empresa = empresa_valida(cnaes_secundarios=["62.04-0-00", 4520001])
        self.assertEqual(empresa.cnaes_secundarios, ["6204000", "4520001"])

    def test_rejeita_campos_invalidos(self):
        casos = {
            "cnpj curto": {"cnpj": "123"},
            "cnpj com letras": {"cnpj": "1111111100011X"},
            "razao vazia": {"razao_social": "   "},
            "cnae com mais de 7 digitos": {"cnae_principal": "12345678"},
            "porte texto": {"porte": "3"},
            "porte booleano": {"porte": True},
            "ibge curto": {"municipio_ibge": "520870"},
        }
        for nome, alteracao in casos.items():
            with self.subTest(nome):
                with self.assertRaises(EmpresaInvalidaError):
                    empresa_valida(**alteracao)

    def test_to_dict_tem_chaves_do_contrato_do_recomendador(self):
        dados = empresa_valida().to_dict()
        for chave in ("cnpj", "razao_social", "cnae_principal", "porte",
                      "municipio_ibge"):
            self.assertIn(chave, dados)

    def test_from_dict(self):
        empresa = Empresa.from_dict({
            "cnpj": "11111111000111",
            "razao_social": "Restaurante A",
            "cnae_principal": "5611201",
            "porte": 3,
            "municipio_ibge": "5208707",
        })
        self.assertEqual(empresa.razao_social, "Restaurante A")

    def test_from_dict_campos_ausentes(self):
        with self.assertRaises(EmpresaInvalidaError):
            Empresa.from_dict({"cnpj": "11111111000111"})

    def test_from_dict_nao_dicionario(self):
        with self.assertRaises(EmpresaInvalidaError):
            Empresa.from_dict(None)


class TestPerfil(unittest.TestCase):

    def test_perfil_valido_tem_pesos_padrao(self):
        perfil = perfil_valido()
        self.assertEqual(
            (perfil.peso_cnae, perfil.peso_porte, perfil.peso_localizacao),
            (50, 25, 25),
        )
        self.assertIsNone(perfil.id)

    def test_normaliza_e_remove_cnaes_duplicados(self):
        perfil = perfil_valido(cnaes_desejados=["62.04-0-00", 6204000, "5611201"])
        self.assertEqual(perfil.cnaes_desejados, ["6204000", "5611201"])

    def test_rejeita_campos_invalidos(self):
        casos = {
            "nome vazio": {"nome": ""},
            "sem cnaes": {"cnaes_desejados": []},
            "cnaes nao e lista": {"cnaes_desejados": "6204000"},
            "cnae invalido": {"cnaes_desejados": ["abc"]},
            "porte texto": {"porte_desejado": "3"},
            "ibge invalido": {"municipio_alvo_ibge": "123"},
            "peso negativo": {"peso_cnae": -1},
            "peso texto": {"peso_porte": "25"},
            "pesos zerados": {
                "peso_cnae": 0, "peso_porte": 0, "peso_localizacao": 0
            },
        }
        for nome, alteracao in casos.items():
            with self.subTest(nome):
                with self.assertRaises(PerfilInvalidoError):
                    perfil_valido(**alteracao)

    def test_um_peso_zero_e_permitido(self):
        perfil = perfil_valido(peso_localizacao=0)
        self.assertEqual(perfil.peso_localizacao, 0)

    def test_to_dict_tem_chaves_do_contrato_do_recomendador(self):
        dados = perfil_valido().to_dict()
        for chave in ("cnaes_desejados", "porte_desejado",
                      "municipio_alvo_ibge"):
            self.assertIn(chave, dados)


class TestLead(unittest.TestCase):

    def test_de_recomendacao_completa(self):
        lead = Lead.de_recomendacao({
            "cnpj": "11111111000111",
            "razao_social": "Restaurante A",
            "pontuacao": 75,
            "justificativas": ["CNAE compatível: +50 pontos"],
        })
        self.assertEqual(lead.cnpj, "11111111000111")
        self.assertEqual(lead.pontuacao, 75)
        self.assertEqual(lead.justificativas, ["CNAE compatível: +50 pontos"])
        self.assertEqual(lead.status, StatusLead.NOVO)

    def test_campos_opcionais_ausentes(self):
        lead = Lead.de_recomendacao({"cnpj": "11111111000111", "pontuacao": 0})
        self.assertEqual(lead.razao_social, "")
        self.assertEqual(lead.justificativas, [])

    def test_razao_social_none_vira_vazio(self):
        lead = Lead.de_recomendacao(
            {"cnpj": "11111111000111", "razao_social": None, "pontuacao": 1}
        )
        self.assertEqual(lead.razao_social, "")

    def test_justificativa_em_texto_vira_lista(self):
        lead = Lead.de_recomendacao(
            {"cnpj": "11111111000111", "pontuacao": 1, "justificativas": "ok"}
        )
        self.assertEqual(lead.justificativas, ["ok"])

    def test_rejeita_itens_fora_do_contrato(self):
        casos = {
            "nao e dicionario": "texto",
            "sem cnpj": {"pontuacao": 10},
            "sem pontuacao": {"cnpj": "11111111000111"},
            "pontuacao texto": {"cnpj": "11111111000111", "pontuacao": "10"},
            "pontuacao booleana": {"cnpj": "11111111000111", "pontuacao": True},
            "pontuacao nan": {"cnpj": "11111111000111", "pontuacao": float("nan")},
            "cnpj invalido": {"cnpj": "123", "pontuacao": 10},
            "justificativas invalidas": {
                "cnpj": "11111111000111", "pontuacao": 10, "justificativas": 5
            },
        }
        for nome, item in casos.items():
            with self.subTest(nome):
                with self.assertRaises(DadosInvalidosError):
                    Lead.de_recomendacao(item)


if __name__ == "__main__":
    unittest.main()

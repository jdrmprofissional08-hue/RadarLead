import unittest
from datetime import datetime

from src.dominio.empresa import Empresa
from src.dominio.lead import Lead, StatusLead
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao, StatusProspeccao
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
            (perfil.peso_segmento, perfil.peso_porte, perfil.peso_localizacao),
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
            "peso negativo": {"peso_segmento": -1},
            "peso texto": {"peso_porte": "25"},
            "pesos zerados": {
                "peso_segmento": 0, "peso_porte": 0, "peso_localizacao": 0
            },
            "pesos nao somam 100": {"peso_segmento": 60},
            "peso acima de 100": {
                "peso_segmento": 110, "peso_porte": -5, "peso_localizacao": -5
            },
            "peso com 3 casas": {
                "peso_segmento": 33.333, "peso_porte": 33.333,
                "peso_localizacao": 33.334,
            },
            "capital negativo": {"capital_minimo": -1},
            "capital texto": {"capital_minimo": "10"},
            "empresa usuaria texto": {"empresa_usuaria_id": "1"},
        }
        for nome, alteracao in casos.items():
            with self.subTest(nome):
                with self.assertRaises(PerfilInvalidoError):
                    perfil_valido(**alteracao)

    def test_um_peso_zero_e_permitido(self):
        perfil = perfil_valido(peso_segmento=75, peso_localizacao=0)
        self.assertEqual(perfil.peso_localizacao, 0)

    def test_pesos_com_decimais_que_somam_100(self):
        perfil = perfil_valido(
            peso_segmento=33.33, peso_porte=33.33, peso_localizacao=33.34
        )
        self.assertEqual(perfil.peso_localizacao, 33.34)

    def test_campos_novos_tem_padrao(self):
        perfil = perfil_valido()
        self.assertEqual(perfil.capital_minimo, 0)
        self.assertIsNone(perfil.empresa_usuaria_id)

    def test_peso_cnae_e_alias_de_peso_segmento(self):
        perfil = perfil_valido(peso_segmento=70, peso_porte=20, peso_localizacao=10)
        self.assertEqual(perfil.peso_cnae, 70)
        self.assertEqual(perfil.to_dict()["peso_cnae"], 70)
        self.assertEqual(perfil.to_dict()["peso_segmento"], 70)

    def test_from_dict_aceita_o_nome_antigo_peso_cnae(self):
        perfil = Perfil.from_dict({
            "nome": "A", "cnaes_desejados": ["6204000"], "porte_desejado": 3,
            "municipio_alvo_ibge": "5208707",
            "peso_cnae": 70, "peso_porte": 20, "peso_localizacao": 10,
        })
        self.assertEqual(perfil.peso_segmento, 70)

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
            "pontuacao acima de 100": {"cnpj": "11111111000111", "pontuacao": 100.5},
            "pontuacao negativa": {"cnpj": "11111111000111", "pontuacao": -1},
            "cnpj invalido": {"cnpj": "123", "pontuacao": 10},
            "justificativas invalidas": {
                "cnpj": "11111111000111", "pontuacao": 10, "justificativas": 5
            },
        }
        for nome, item in casos.items():
            with self.subTest(nome):
                with self.assertRaises(DadosInvalidosError):
                    Lead.de_recomendacao(item)


class TestSerializacao(unittest.TestCase):
    """to_dict / from_dict: o que o repositório JSON usa para gravar e ler."""

    def test_perfil_ida_e_volta(self):
        perfil = perfil_valido(peso_segmento=70, peso_porte=20, peso_localizacao=10)
        perfil.id = 4

        self.assertEqual(Perfil.from_dict(perfil.to_dict()), perfil)

    def test_perfil_from_dict_sem_pesos_usa_os_padroes(self):
        perfil = Perfil.from_dict({
            "nome": "A",
            "cnaes_desejados": ["6204000"],
            "porte_desejado": 3,
            "municipio_alvo_ibge": "5208707",
        })
        self.assertEqual(
            (perfil.peso_segmento, perfil.peso_porte, perfil.peso_localizacao),
            (50, 25, 25),
        )
        self.assertIsNone(perfil.id)

    def test_perfil_from_dict_invalido(self):
        base = perfil_valido().to_dict()
        casos = {
            "nao e dicionario": None,
            "campo ausente": {"nome": "A"},
            "id booleano": {**base, "id": True},
            "id texto": {**base, "id": "1"},
            "campo invalido": {**base, "porte_desejado": "x"},
        }
        for nome, dados in casos.items():
            with self.subTest(nome):
                with self.assertRaises(PerfilInvalidoError):
                    Perfil.from_dict(dados)

    def test_empresa_ida_e_volta(self):
        empresa = empresa_valida(
            cnaes_secundarios=["4520001"], cep="75700000",
            latitude=-18.16, longitude=-47.94,
        )
        self.assertEqual(Empresa.from_dict(empresa.to_dict()), empresa)

    def test_lead_ida_e_volta_com_status(self):
        lead = Lead("11111111000111", "A", 75.5, ["ok"], StatusLead.CONVERTIDO)
        self.assertEqual(Lead.from_dict(lead.to_dict()), lead)
        self.assertEqual(lead.to_dict()["status"], "convertido")

    def test_lead_from_dict_sem_status_e_novo(self):
        lead = Lead.from_dict({"cnpj": "11111111000111", "pontuacao": 1})
        self.assertEqual(lead.status, StatusLead.NOVO)

    def test_lead_from_dict_status_invalido(self):
        for status in ("inventado", 3, ["novo"]):
            with self.subTest(status=status):
                with self.assertRaises(DadosInvalidosError):
                    Lead.from_dict({
                        "cnpj": "11111111000111", "pontuacao": 1, "status": status,
                    })

    def test_prospeccao_ida_e_volta(self):
        prospeccao = Prospeccao(
            perfil_id=2,
            leads=[Lead("11111111000111", "A", 100, ["x"], StatusLead.CONTATADO)],
            total_empresas_avaliadas=7,
            criada_em=datetime(2026, 11, 17, 18, 30, 5, 123456),
            id=9,
        )
        self.assertEqual(Prospeccao.from_dict(prospeccao.to_dict()), prospeccao)

    def test_prospeccao_tem_status_concluida_por_padrao(self):
        self.assertEqual(Prospeccao(perfil_id=1).status, StatusProspeccao.CONCLUIDA)
        self.assertEqual(Prospeccao(perfil_id=1).to_dict()["status"], "concluida")

    def test_prospeccao_ida_e_volta_com_status_erro(self):
        prospeccao = Prospeccao(perfil_id=2, status=StatusProspeccao.ERRO, id=3)
        self.assertEqual(Prospeccao.from_dict(prospeccao.to_dict()), prospeccao)

    def test_prospeccao_from_dict_invalida(self):
        base = Prospeccao(perfil_id=1).to_dict()
        casos = {
            "nao e dicionario": [],
            "campo ausente": {"perfil_id": 1},
            "perfil_id texto": {**base, "perfil_id": "1"},
            "total negativo": {**base, "total_empresas_avaliadas": -1},
            "id texto": {**base, "id": "1"},
            "status invalido": {**base, "status": "pendente"},
            "data invalida": {**base, "criada_em": "ontem"},
            "data nao e texto": {**base, "criada_em": 20261117},
            "leads nao e lista": {**base, "leads": {}},
            "lead invalido": {**base, "leads": [{"cnpj": "123"}]},
        }
        for nome, dados in casos.items():
            with self.subTest(nome):
                with self.assertRaises(DadosInvalidosError):
                    Prospeccao.from_dict(dados)


if __name__ == "__main__":
    unittest.main()

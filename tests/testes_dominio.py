import unittest
from datetime import datetime

from src.dominio.empresa import Empresa
from src.dominio.empresa_usuaria import EmpresaUsuaria, Produto
from src.dominio import validacao
from src.dominio.lead import Lead, StatusLead
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao, StatusProspeccao
from src.excecoes import (
    DadosInvalidosError,
    EmpresaInvalidaError,
    EmpresaUsuariaInvalidaError,
    PerfilInvalidoError,
    ProdutoInvalidoError,
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


class TestEmpresaDadosCadastrais(unittest.TestCase):

    def test_sem_dados_cadastrais_nada_e_inventado(self):
        empresa = empresa_valida()
        self.assertIsNone(empresa.situacao_cadastral)
        self.assertFalse(empresa.ativa)
        self.assertIsNone(empresa.natureza_juridica)
        self.assertIsNone(empresa.capital_social)

    def test_normaliza_situacao_natureza_e_datas(self):
        empresa = empresa_valida(
            situacao_cadastral="02", natureza_juridica=2062, capital_social=10,
            data_inicio_atividade="2015-03-10T00:00:00", data_situacao="2020-01-02",
        )
        self.assertEqual(empresa.situacao_cadastral, 2)
        self.assertTrue(empresa.ativa)
        self.assertEqual(empresa.natureza_juridica, "2062")
        self.assertEqual(str(empresa.data_inicio_atividade), "2015-03-10")
        self.assertEqual(str(empresa.data_situacao), "2020-01-02")

    def test_so_situacao_2_e_ativa(self):
        for codigo in (1, 3, 4, 8):
            with self.subTest(codigo):
                self.assertFalse(empresa_valida(situacao_cadastral=codigo).ativa)

    def test_rejeita_dados_cadastrais_invalidos(self):
        casos = {
            "situacao zero (e o marcador do banco)": {"situacao_cadastral": 0},
            "situacao texto": {"situacao_cadastral": "ativa"},
            "situacao booleana": {"situacao_cadastral": True},
            "situacao com 3 digitos": {"situacao_cadastral": 100},
            "natureza zerada (e o marcador do banco)": {"natureza_juridica": "0000"},
            "natureza longa": {"natureza_juridica": "20620"},
            "capital negativo": {"capital_social": -1},
            "capital texto": {"capital_social": "10"},
            "capital NaN": {"capital_social": float("nan")},
            "data invalida": {"data_inicio_atividade": "ontem"},
            "data no formato brasileiro": {"data_situacao": "10/03/2015"},
            "data marcador do banco": {"data_inicio_atividade": "1900-01-01"},
            "data numero": {"data_inicio_atividade": 20150310},
        }
        for nome, alteracao in casos.items():
            with self.subTest(nome):
                with self.assertRaises(EmpresaInvalidaError):
                    empresa_valida(**alteracao)

    def test_ida_e_volta_com_dados_cadastrais(self):
        empresa = empresa_valida(
            situacao_cadastral=2, natureza_juridica="2062", capital_social=1500.5,
            data_inicio_atividade="2015-03-10", data_situacao="2015-03-10",
        )
        dados = empresa.to_dict()

        self.assertEqual(dados["situacao_cadastral"], 2)          # contrato do recomendador
        self.assertEqual(dados["data_inicio_atividade"], "2015-03-10")
        self.assertEqual(Empresa.from_dict(dados), empresa)

    def test_from_dict_antigo_sem_os_campos_novos_continua_valido(self):
        empresa = Empresa.from_dict({
            "cnpj": "11111111000111", "razao_social": "A",
            "cnae_principal": "5611201", "porte": 3, "municipio_ibge": "5208707",
        })
        self.assertIsNone(empresa.situacao_cadastral)


class TestPesosDoPerfil(unittest.TestCase):

    def test_peso_redondo_vira_inteiro(self):
        """O recomendador exige inteiros; o banco devolve 50.0."""
        perfil = perfil_valido(
            peso_segmento=50.0, peso_porte=30.0, peso_localizacao=20.0
        )
        for peso in (perfil.peso_segmento, perfil.peso_porte,
                     perfil.peso_localizacao):
            self.assertIs(type(peso), int)
        dados = perfil.to_dict()
        self.assertIs(type(dados["peso_cnae"]), int)
        self.assertIs(type(dados["peso_segmento"]), int)

    def test_peso_decimal_continua_decimal(self):
        perfil = perfil_valido(
            peso_segmento=33.33, peso_porte=33.33, peso_localizacao=33.34
        )
        self.assertEqual(perfil.peso_segmento, 33.33)
        self.assertIs(type(perfil.peso_localizacao), float)


class TestPorteDoPerfil(unittest.TestCase):

    def test_portes_da_receita_sao_aceitos(self):
        for porte in (0, 1, 3, 5):
            with self.subTest(porte):
                self.assertEqual(perfil_valido(porte_desejado=porte).porte_desejado, porte)

    def test_outros_portes_sao_recusados(self):
        for porte in (2, 4, 6, -1, 99):
            with self.subTest(porte):
                with self.assertRaises(PerfilInvalidoError):
                    perfil_valido(porte_desejado=porte)


class TestEmpresaUsuaria(unittest.TestCase):

    def test_normaliza_e_valida(self):
        e = EmpresaUsuaria(nome="  Minha  ", cnpj="11.222.333/0001-81", email=" a@b.co ")
        self.assertEqual((e.nome, e.cnpj, e.email, e.id), ("Minha", "11222333000181", "a@b.co", None))

    def test_dados_invalidos(self):
        base = dict(nome="A", cnpj="11222333000181", email="a@b.co")
        casos = {
            "digito errado": {"cnpj": "11222333000182"},
            "repetido": {"cnpj": "11111111111111"},
            "curto": {"cnpj": "123"},
            "letras": {"cnpj": "abc"},
            "cnpj bool": {"cnpj": True},
            "email sem arroba": {"email": "abc"},
            "email sem ponto": {"email": "a@b"},
            "email com espaco": {"email": "a b@c.com"},
            "email enorme": {"email": "a@" + "b" * 260 + ".com"},
            "nome vazio": {"nome": " "},
            "id texto": {"id": "1"},
        }
        for nome, mudanca in casos.items():
            with self.subTest(nome):
                with self.assertRaises(EmpresaUsuariaInvalidaError):
                    EmpresaUsuaria(**{**base, **mudanca})

    def test_ida_e_volta(self):
        e = EmpresaUsuaria(nome="A", cnpj="11222333000181", email="a@b.co", id=3)
        self.assertEqual(EmpresaUsuaria.from_dict(e.to_dict()), e)
        with self.assertRaises(EmpresaUsuariaInvalidaError):
            EmpresaUsuaria.from_dict({"nome": "A"})

    def test_digitos_verificadores_conhecidos(self):
        for cnpj in ("11222333000181", "11444777000161", "12345678000195"):
            self.assertTrue(validacao.cnpj_tem_digitos_validos(cnpj), cnpj)
        for cnpj in ("11222333000180", "00000000000000", "1122233300018", "1122233300018a"):
            self.assertFalse(validacao.cnpj_tem_digitos_validos(cnpj), cnpj)


class TestProduto(unittest.TestCase):

    def test_descricao_opcional_e_aparada(self):
        self.assertIsNone(Produto(nome="A").descricao)
        self.assertIsNone(Produto(nome="A", descricao="   ").descricao)
        self.assertEqual(Produto(nome=" A ", descricao=" x ").to_dict(),
                         {"id": None, "empresa_usuaria_id": None, "nome": "A", "descricao": "x"})

    def test_dados_invalidos(self):
        for nome, dados in {
            "nome vazio": {"nome": ""}, "nome numero": {"nome": 1},
            "descricao numero": {"nome": "A", "descricao": 3},
            "empresa texto": {"nome": "A", "empresa_usuaria_id": "1"},
            "id bool": {"nome": "A", "id": True},
        }.items():
            with self.subTest(nome):
                with self.assertRaises(ProdutoInvalidoError):
                    Produto(**dados)

    def test_ida_e_volta(self):
        p = Produto(nome="A", descricao="d", empresa_usuaria_id=1, id=2)
        self.assertEqual(Produto.from_dict(p.to_dict()), p)


class TestProdutoDoPerfil(unittest.TestCase):

    def test_padrao_e_nulo_e_vai_para_o_dicionario(self):
        perfil = perfil_valido()
        self.assertIsNone(perfil.produto_id)
        self.assertIsNone(perfil.to_dict()["produto_id"])
        self.assertEqual(perfil_valido(produto_id=4).to_dict()["produto_id"], 4)

    def test_ida_e_volta_e_arquivos_antigos_sem_o_campo(self):
        perfil = perfil_valido(produto_id=4)
        self.assertEqual(Perfil.from_dict(perfil.to_dict()).produto_id, 4)
        antigo = perfil_valido().to_dict()
        del antigo["produto_id"]
        self.assertIsNone(Perfil.from_dict(antigo).produto_id)

    def test_tipo_invalido(self):
        for valor in ("1", 1.5, True, [1]):
            with self.subTest(valor):
                with self.assertRaises(PerfilInvalidoError):
                    perfil_valido(produto_id=valor)


class TestChaveDeNome(unittest.TestCase):

    def test_ignora_caixa_acento_e_espacos_das_pontas(self):
        self.assertEqual(validacao.chave_de_nome("  TI em Goiânia "),
                         validacao.chave_de_nome("ti EM goiania"))
        self.assertNotEqual(validacao.chave_de_nome("TI A"), validacao.chave_de_nome("TI B"))


if __name__ == "__main__":
    unittest.main()

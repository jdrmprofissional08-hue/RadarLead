import unittest

from src.dominio.empresa import Empresa
from src.dominio.lead import StatusLead
from src.excecoes import (
    PerfilInvalidoError,
    PerfilNaoEncontradoError,
    ProspeccaoNaoEncontradaError,
    RecomendadorError,
    RadarLeadError,
)
from src.persistencia.repositorio_memoria import RepositorioMemoria
from src.servicos.servico_perfil import ServicoPerfil
from src.servicos.servico_prospeccao import ServicoProspeccao


class RecomendadorFalso:
    """Devolve uma resposta pronta e guarda o que recebeu."""

    def __init__(self, resposta):
        self.resposta = resposta
        self.recebeu = None

    def recomendar(self, empresas, perfil):
        self.recebeu = (empresas, perfil)
        return self.resposta


class RecomendadorQueFalha:
    def __init__(self, erro):
        self.erro = erro

    def recomendar(self, empresas, perfil):
        raise self.erro


def empresa(cnpj, razao_social="Empresa"):
    return Empresa(
        cnpj=cnpj,
        razao_social=razao_social,
        cnae_principal="6204000",
        porte=3,
        municipio_ibge="5208707",
    )


DADOS_PERFIL = {
    "nome": "Software em Catalão",
    "cnaes_desejados": ["6204000"],
    "porte_desejado": 3,
    "municipio_alvo_ibge": "5208707",
}


class TestServicoPerfil(unittest.TestCase):

    def setUp(self):
        self.repo = RepositorioMemoria()
        self.servico = ServicoPerfil(self.repo)

    def test_cadastrar_salva_com_id(self):
        perfil = self.servico.cadastrar(**DADOS_PERFIL)
        self.assertEqual(perfil.id, 1)
        self.assertEqual(self.repo.buscar_perfil(1).nome, "Software em Catalão")

    def test_cadastrar_com_pesos_personalizados(self):
        perfil = self.servico.cadastrar(
            **DADOS_PERFIL, peso_segmento=70, peso_porte=20, peso_localizacao=10
        )
        self.assertEqual(
            (perfil.peso_segmento, perfil.peso_porte, perfil.peso_localizacao),
            (70, 20, 10),
        )

    def test_cadastro_invalido_nao_salva(self):
        with self.assertRaises(PerfilInvalidoError):
            self.servico.cadastrar(**{**DADOS_PERFIL, "cnaes_desejados": []})
        self.assertEqual(self.servico.listar(), [])

    def test_buscar_e_listar(self):
        self.servico.cadastrar(**DADOS_PERFIL)
        self.servico.cadastrar(**{**DADOS_PERFIL, "nome": "Outro"})

        self.assertEqual(self.servico.buscar(2).nome, "Outro")
        self.assertEqual(len(self.servico.listar()), 2)

    def test_buscar_inexistente(self):
        with self.assertRaises(PerfilNaoEncontradoError):
            self.servico.buscar(10)


class TestServicoProspeccao(unittest.TestCase):

    def setUp(self):
        self.repo = RepositorioMemoria()
        self.perfil = ServicoPerfil(self.repo).cadastrar(**DADOS_PERFIL)
        self.repo.salvar_empresas([
            empresa("11111111000111", "A"),
            empresa("22222222000122", "B"),
        ])

    def servico(self, recomendador, **extra):
        return ServicoProspeccao(self.repo, recomendador, **extra)

    def test_fluxo_completo_gera_leads_ordenados_e_salva(self):
        recomendador = RecomendadorFalso([
            {"cnpj": "22222222000122", "razao_social": "B", "pontuacao": 25,
             "justificativas": ["Município compatível: +25 pontos"]},
            {"cnpj": "11111111000111", "razao_social": "A", "pontuacao": 100,
             "justificativas": ["CNAE compatível: +50 pontos"]},
        ])

        prospeccao = self.servico(recomendador).executar(self.perfil.id)

        self.assertEqual(prospeccao.id, 1)
        self.assertEqual(prospeccao.perfil_id, self.perfil.id)
        self.assertEqual(prospeccao.total_empresas_avaliadas, 2)
        self.assertEqual(
            [lead.cnpj for lead in prospeccao.leads],
            ["11111111000111", "22222222000122"],
        )
        self.assertEqual(prospeccao.leads[0].status, StatusLead.NOVO)
        self.assertEqual(
            prospeccao.leads[0].justificativas, ["CNAE compatível: +50 pontos"]
        )
        self.assertEqual(len(self.repo.buscar_prospeccao(1).leads), 2)

    def test_recomendador_recebe_dicionarios_do_contrato(self):
        recomendador = RecomendadorFalso([])
        self.servico(recomendador).executar(self.perfil.id)

        empresas, perfil = recomendador.recebeu
        self.assertEqual(len(empresas), 2)
        self.assertEqual(empresas[0]["cnpj"], "11111111000111")
        self.assertEqual(empresas[0]["cnae_principal"], "6204000")
        self.assertEqual(perfil["cnaes_desejados"], ["6204000"])
        self.assertEqual(perfil["porte_desejado"], 3)
        self.assertEqual(perfil["municipio_alvo_ibge"], "5208707")

    def test_sem_empresas_gera_prospeccao_vazia(self):
        repo = RepositorioMemoria()
        perfil = ServicoPerfil(repo).cadastrar(**DADOS_PERFIL)

        prospeccao = ServicoProspeccao(
            repo, RecomendadorFalso([])
        ).executar(perfil.id)

        self.assertEqual(prospeccao.leads, [])
        self.assertEqual(prospeccao.total_empresas_avaliadas, 0)

    def test_usa_fonte_de_empresas_quando_informada(self):
        recomendador = RecomendadorFalso([])
        fonte = lambda perfil: [empresa("33333333000133", "C")]

        prospeccao = self.servico(
            recomendador, fonte_empresas=fonte
        ).executar(self.perfil.id)

        self.assertEqual(prospeccao.total_empresas_avaliadas, 1)
        self.assertEqual(recomendador.recebeu[0][0]["cnpj"], "33333333000133")

    def test_perfil_inexistente(self):
        with self.assertRaises(PerfilNaoEncontradoError):
            self.servico(RecomendadorFalso([])).executar(99)

    def test_falha_do_recomendador_vira_recomendador_error(self):
        servico = self.servico(RecomendadorQueFalha(KeyError("porte")))

        with self.assertRaises(RecomendadorError):
            servico.executar(self.perfil.id)

        self.assertEqual(self.repo.listar_prospeccoes(), [])

    def test_excecao_do_projeto_e_repassada_sem_troca(self):
        class ErroEspecifico(RadarLeadError):
            pass

        servico = self.servico(RecomendadorQueFalha(ErroEspecifico("x")))

        with self.assertRaises(ErroEspecifico):
            servico.executar(self.perfil.id)

    def test_resposta_que_nao_e_lista(self):
        with self.assertRaises(RecomendadorError):
            self.servico(RecomendadorFalso({"cnpj": "x"})).executar(self.perfil.id)

    def test_resposta_fora_do_contrato_nao_salva_nada(self):
        recomendador = RecomendadorFalso([{"cnpj": "11111111000111"}])

        with self.assertRaises(RecomendadorError):
            self.servico(recomendador).executar(self.perfil.id)

        self.assertEqual(self.repo.listar_prospeccoes(), [])

    def test_buscar_e_listar_prospeccoes(self):
        servico = self.servico(RecomendadorFalso([]))
        servico.executar(self.perfil.id)
        servico.executar(self.perfil.id)

        self.assertEqual(servico.buscar(2).id, 2)
        self.assertEqual(len(servico.listar()), 2)
        self.assertEqual(len(servico.listar(perfil_id=self.perfil.id)), 2)
        self.assertEqual(servico.listar(perfil_id=99), [])

    def test_buscar_prospeccao_inexistente(self):
        with self.assertRaises(ProspeccaoNaoEncontradaError):
            self.servico(RecomendadorFalso([])).buscar(5)


if __name__ == "__main__":
    unittest.main()

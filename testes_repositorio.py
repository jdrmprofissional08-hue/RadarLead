"""Testes de contrato do Repositorio.

As mesmas verificações rodam contra cada implementação (memória e JSON).
O repositório PostgreSQL entra aqui também, mas só roda se houver um banco
de teste (ver tests/apoio_postgres.py); sem ele, essas classes são puladas.
"""

import tempfile
import unittest
from pathlib import Path

from src.dominio.empresa import Empresa
from src.dominio.lead import Lead
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao
from src.excecoes import (
    EmpresaNaoEncontradaError,
    PerfilNaoEncontradoError,
    ProspeccaoNaoEncontradaError,
)
from tests import apoio_postgres
from src.persistencia.repositorio_json import RepositorioJson
from src.persistencia.repositorio_memoria import RepositorioMemoria


def novo_perfil(nome="Perfil A"):
    return Perfil(
        nome=nome,
        cnaes_desejados=["6204000"],
        porte_desejado=3,
        municipio_alvo_ibge="5208707",
    )


def nova_empresa(cnpj="11111111000111", razao_social="Empresa A"):
    return Empresa(
        cnpj=cnpj,
        razao_social=razao_social,
        cnae_principal="6204000",
        porte=3,
        municipio_ibge="5208707",
        cep="75700000",  # o PostgreSQL obtém o município pelo CEP
    )


def nova_prospeccao(perfil_id=1):
    lead = Lead(cnpj="11111111000111", razao_social="A", pontuacao=50)
    return Prospeccao(perfil_id=perfil_id, leads=[lead])


# --- O contrato (mixins: não rodam sozinhos, só nas classes concretas) --------

class ContratoPerfis:

    def setUp(self):
        self.repo = self.criar_repositorio()

    def test_salvar_atribui_ids_sequenciais(self):
        a = self.repo.salvar_perfil(novo_perfil("A"))
        b = self.repo.salvar_perfil(novo_perfil("B"))
        self.assertEqual((a.id, b.id), (1, 2))

    def test_buscar_devolve_o_perfil_salvo(self):
        salvo = self.repo.salvar_perfil(novo_perfil("A"))
        self.assertEqual(self.repo.buscar_perfil(salvo.id).nome, "A")

    def test_buscar_inexistente(self):
        with self.assertRaises(PerfilNaoEncontradoError):
            self.repo.buscar_perfil(99)

    def test_listar_em_ordem_de_cadastro(self):
        self.repo.salvar_perfil(novo_perfil("A"))
        self.repo.salvar_perfil(novo_perfil("B"))
        self.assertEqual([p.nome for p in self.repo.listar_perfis()], ["A", "B"])

    def test_listar_vazio(self):
        self.assertEqual(self.repo.listar_perfis(), [])

    def test_atualizar_perfil_existente(self):
        perfil = self.repo.salvar_perfil(novo_perfil("A"))
        perfil.nome = "A atualizado"
        self.repo.salvar_perfil(perfil)

        self.assertEqual(self.repo.buscar_perfil(perfil.id).nome, "A atualizado")
        self.assertEqual(len(self.repo.listar_perfis()), 1)

    def test_atualizar_perfil_inexistente(self):
        perfil = novo_perfil()
        perfil.id = 42
        with self.assertRaises(PerfilNaoEncontradoError):
            self.repo.salvar_perfil(perfil)

    def test_alterar_objeto_buscado_nao_muda_o_repositorio(self):
        salvo = self.repo.salvar_perfil(novo_perfil("A"))
        buscado = self.repo.buscar_perfil(salvo.id)
        buscado.nome = "alterado"
        buscado.cnaes_desejados.append("1111111")

        original = self.repo.buscar_perfil(salvo.id)
        self.assertEqual(original.nome, "A")
        self.assertEqual(original.cnaes_desejados, ["6204000"])

    def test_alterar_objeto_depois_de_salvar_nao_muda_o_repositorio(self):
        perfil = self.repo.salvar_perfil(novo_perfil("A"))
        perfil.nome = "alterado sem salvar"
        self.assertEqual(self.repo.buscar_perfil(perfil.id).nome, "A")


class ContratoEmpresas:

    def setUp(self):
        self.repo = self.criar_repositorio()

    def test_salvar_e_buscar(self):
        self.repo.salvar_empresa(nova_empresa())
        self.assertEqual(
            self.repo.buscar_empresa("11111111000111").razao_social, "Empresa A"
        )

    def test_salvar_mesmo_cnpj_atualiza(self):
        self.repo.salvar_empresa(nova_empresa(razao_social="Antiga"))
        self.repo.salvar_empresa(nova_empresa(razao_social="Nova"))

        self.assertEqual(len(self.repo.listar_empresas()), 1)
        self.assertEqual(
            self.repo.buscar_empresa("11111111000111").razao_social, "Nova"
        )

    def test_salvar_varias(self):
        self.repo.salvar_empresas([
            nova_empresa("11111111000111"),
            nova_empresa("22222222000122"),
        ])
        self.assertEqual(len(self.repo.listar_empresas()), 2)

    def test_buscar_inexistente(self):
        with self.assertRaises(EmpresaNaoEncontradaError):
            self.repo.buscar_empresa("00000000000000")

    def test_alterar_objeto_buscado_nao_muda_o_repositorio(self):
        self.repo.salvar_empresa(nova_empresa())
        buscada = self.repo.buscar_empresa("11111111000111")
        buscada.razao_social = "alterada"

        self.assertEqual(
            self.repo.buscar_empresa("11111111000111").razao_social, "Empresa A"
        )


class ContratoProspeccoes:

    def setUp(self):
        self.repo = self.criar_repositorio()

    def test_salvar_atribui_id_e_busca(self):
        salva = self.repo.salvar_prospeccao(nova_prospeccao())
        self.assertEqual(salva.id, 1)

        buscada = self.repo.buscar_prospeccao(1)
        self.assertEqual(buscada.leads[0].cnpj, "11111111000111")

    def test_buscar_inexistente(self):
        with self.assertRaises(ProspeccaoNaoEncontradaError):
            self.repo.buscar_prospeccao(7)

    def test_listar_filtrando_por_perfil(self):
        self.repo.salvar_prospeccao(nova_prospeccao(perfil_id=1))
        self.repo.salvar_prospeccao(nova_prospeccao(perfil_id=2))
        self.repo.salvar_prospeccao(nova_prospeccao(perfil_id=1))

        self.assertEqual(len(self.repo.listar_prospeccoes()), 3)
        self.assertEqual(len(self.repo.listar_prospeccoes(perfil_id=1)), 2)
        self.assertEqual(self.repo.listar_prospeccoes(perfil_id=9), [])

    def test_alterar_lead_buscado_nao_muda_o_repositorio(self):
        self.repo.salvar_prospeccao(nova_prospeccao())
        buscada = self.repo.buscar_prospeccao(1)
        buscada.leads[0].pontuacao = 0

        self.assertEqual(self.repo.buscar_prospeccao(1).leads[0].pontuacao, 50)


# --- Como criar o repositório de cada implementação ---------------------------

class UsaMemoria:
    def criar_repositorio(self):
        return RepositorioMemoria()


class UsaJson:
    def criar_repositorio(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        return RepositorioJson(Path(pasta.name) / "dados.json")


# --- Classes concretas (são estas que o unittest executa) ---------------------

class TestPerfisMemoria(UsaMemoria, ContratoPerfis, unittest.TestCase):
    pass


class TestEmpresasMemoria(UsaMemoria, ContratoEmpresas, unittest.TestCase):
    pass


class TestProspeccoesMemoria(UsaMemoria, ContratoProspeccoes, unittest.TestCase):
    pass


class TestPerfisJson(UsaJson, ContratoPerfis, unittest.TestCase):
    pass


class TestEmpresasJson(UsaJson, ContratoEmpresas, unittest.TestCase):
    pass


class TestProspeccoesJson(UsaJson, ContratoProspeccoes, unittest.TestCase):
    pass




class UsaPostgres:
    def criar_repositorio(self):
        return apoio_postgres.criar_repositorio_postgres()


@apoio_postgres.requer_postgres
class TestPerfisPostgres(UsaPostgres, ContratoPerfis, unittest.TestCase):
    pass


@apoio_postgres.requer_postgres
class TestEmpresasPostgres(UsaPostgres, ContratoEmpresas, unittest.TestCase):
    pass


@apoio_postgres.requer_postgres
class TestProspeccoesPostgres(UsaPostgres, ContratoProspeccoes, unittest.TestCase):

    def setUp(self):
        super().setUp()
        # no banco, prospecção e lead exigem perfil e estabelecimento existentes
        self.repo.salvar_perfil(novo_perfil("P1"))
        self.repo.salvar_perfil(novo_perfil("P2"))
        self.repo.salvar_empresa(nova_empresa())


if __name__ == "__main__":
    unittest.main()

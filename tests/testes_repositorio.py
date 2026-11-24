"""Testes de contrato do Repositorio.

As mesmas verificações rodam contra cada implementação (memória e JSON).
O repositório PostgreSQL entra aqui também, mas só roda se houver um banco
de teste (ver tests/apoio_postgres.py); sem ele, essas classes são puladas.
"""

import tempfile
import unittest
from pathlib import Path

from src.dominio.empresa import Empresa
from src.dominio.empresa_usuaria import EmpresaUsuaria, Produto
from src.dominio.lead import Lead
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao
from src.excecoes import (
    DadosInvalidosError,
    DuplicadoError,
    EmpresaNaoEncontradaError,
    EmpresaUsuariaNaoEncontradaError,
    PerfilNaoEncontradoError,
    ProdutoNaoEncontradoError,
    ProspeccaoNaoEncontradaError,
)
from tests import apoio_mysql, apoio_postgres
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


def nova_empresa_usuaria(nome="Minha Empresa", cnpj="11222333000181", email="contato@minha.com"):
    return EmpresaUsuaria(nome=nome, cnpj=cnpj, email=email)


class ContratoEmpresaUsuariaEProdutos:
    """Empresa usuária atual, produtos e o produto do perfil."""

    def setUp(self):
        self.repo = self.criar_repositorio()

    def cadastrar_empresa(self):
        return self.repo.salvar_empresa_usuaria_atual(nova_empresa_usuaria())

    def test_sem_cadastro(self):
        with self.assertRaises(EmpresaUsuariaNaoEncontradaError):
            self.repo.buscar_empresa_usuaria_atual()

    def test_cadastra_e_busca(self):
        salva = self.cadastrar_empresa()
        self.assertEqual(salva.id, 1)
        lida = self.repo.buscar_empresa_usuaria_atual()
        self.assertEqual(lida.to_dict(), {"id": 1, "nome": "Minha Empresa",
                                          "cnpj": "11222333000181",
                                          "email": "contato@minha.com"})
        self.assertEqual(self.repo.empresa_usuaria_atual_id(), 1)

    def test_salvar_de_novo_atualiza_a_mesma_empresa(self):
        self.cadastrar_empresa()
        self.repo.salvar_empresa_usuaria_atual(
            nova_empresa_usuaria(nome="Outro Nome", cnpj="11444777000161", email="novo@x.com"))
        lida = self.repo.buscar_empresa_usuaria_atual()
        self.assertEqual((lida.id, lida.nome, lida.cnpj, lida.email),
                         (1, "Outro Nome", "11444777000161", "novo@x.com"))

    def test_objeto_buscado_e_uma_copia(self):
        self.cadastrar_empresa()
        lida = self.repo.buscar_empresa_usuaria_atual()
        lida.nome = "alterado"
        self.assertEqual(self.repo.buscar_empresa_usuaria_atual().nome, "Minha Empresa")

    def test_perfil_novo_pertence_a_empresa_atual(self):
        empresa = self.cadastrar_empresa()
        perfil = self.repo.salvar_perfil(novo_perfil())
        self.assertEqual(perfil.empresa_usuaria_id, empresa.id)
        self.assertEqual(self.repo.buscar_perfil(perfil.id).empresa_usuaria_id, empresa.id)

    def test_empresa_provisoria_nao_conta_como_cadastro_e_e_substituida(self):
        perfil = self.repo.salvar_perfil(novo_perfil())  # cria a empresa provisória
        self.assertIsNotNone(perfil.empresa_usuaria_id)
        self.assertEqual(self.repo.empresa_usuaria_atual_id(), perfil.empresa_usuaria_id)
        with self.assertRaises(EmpresaUsuariaNaoEncontradaError):
            self.repo.buscar_empresa_usuaria_atual()

        salva = self.cadastrar_empresa()
        self.assertEqual(salva.id, perfil.empresa_usuaria_id)
        self.assertEqual(self.repo.buscar_perfil(perfil.id).empresa_usuaria_id, salva.id)

    def test_produto_ida_e_volta(self):
        empresa = self.cadastrar_empresa()
        a = self.repo.salvar_produto(Produto(nome="Consultoria", descricao="Horas",
                                             empresa_usuaria_id=empresa.id))
        b = self.repo.salvar_produto(Produto(nome="Suporte", empresa_usuaria_id=empresa.id))
        self.assertEqual((a.id, b.id), (1, 2))
        self.assertEqual(self.repo.buscar_produto(1, empresa.id).to_dict(), {
            "id": 1, "empresa_usuaria_id": empresa.id, "nome": "Consultoria",
            "descricao": "Horas"})
        self.assertIsNone(self.repo.buscar_produto(2, empresa.id).descricao)
        self.assertEqual([p.nome for p in self.repo.listar_produtos(empresa.id)],
                         ["Consultoria", "Suporte"])

    def test_atualizar_produto(self):
        empresa = self.cadastrar_empresa()
        produto = self.repo.salvar_produto(Produto(nome="A", empresa_usuaria_id=empresa.id))
        produto.nome, produto.descricao = "A2", "nova"
        self.repo.salvar_produto(produto)
        lido = self.repo.buscar_produto(produto.id, empresa.id)
        self.assertEqual((lido.nome, lido.descricao), ("A2", "nova"))
        self.assertEqual(len(self.repo.listar_produtos(empresa.id)), 1)

    def test_atualizar_produto_inexistente(self):
        empresa = self.cadastrar_empresa()
        with self.assertRaises(ProdutoNaoEncontradoError):
            self.repo.salvar_produto(Produto(id=99, nome="X", empresa_usuaria_id=empresa.id))

    def test_nome_repetido_ignora_caixa_e_acento_mas_o_proprio_produto_pode_salvar(self):
        empresa = self.cadastrar_empresa()
        produto = self.repo.salvar_produto(
            Produto(nome="Consultoria", empresa_usuaria_id=empresa.id))
        with self.assertRaises(DuplicadoError):
            self.repo.salvar_produto(Produto(nome="consultória", empresa_usuaria_id=empresa.id))
        # salvar o mesmo produto de novo (mesmo nome) não é duplicidade
        self.repo.salvar_produto(produto)
        self.assertEqual(len(self.repo.listar_produtos(empresa.id)), 1)

    def test_produto_de_empresa_inexistente(self):
        with self.assertRaises(EmpresaUsuariaNaoEncontradaError):
            self.repo.salvar_produto(Produto(nome="X", empresa_usuaria_id=99))

    def test_produto_so_e_visto_pela_empresa_dona(self):
        empresa = self.cadastrar_empresa()
        produto = self.repo.salvar_produto(Produto(nome="X", empresa_usuaria_id=empresa.id))
        with self.assertRaises(ProdutoNaoEncontradoError):
            self.repo.buscar_produto(produto.id, empresa.id + 1)
        self.assertEqual(self.repo.listar_produtos(empresa.id + 1), [])

    def test_perfil_com_produto_e_remocao(self):
        empresa = self.cadastrar_empresa()
        produto = self.repo.salvar_produto(Produto(nome="X", empresa_usuaria_id=empresa.id))
        perfil = novo_perfil()
        perfil.produto_id = produto.id
        self.repo.salvar_perfil(perfil)
        self.assertEqual(self.repo.buscar_perfil(perfil.id).produto_id, produto.id)
        self.assertEqual(self.repo.listar_perfis()[0].produto_id, produto.id)

        perfil.produto_id = None
        self.repo.salvar_perfil(perfil)
        self.assertIsNone(self.repo.buscar_perfil(perfil.id).produto_id)

    def test_perfil_com_produto_inexistente_nao_e_salvo(self):
        self.cadastrar_empresa()
        perfil = novo_perfil()
        perfil.produto_id = 99
        with self.assertRaises(DadosInvalidosError):
            self.repo.salvar_perfil(perfil)
        self.assertEqual(self.repo.listar_perfis(), [])
        self.assertIsNone(perfil.id)


# --- Como criar o repositório de cada implementação ---------------------------

class UsaMemoria:
    def criar_repositorio(self):
        return RepositorioMemoria()


class UsaJson:
    def criar_repositorio(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        return RepositorioJson(Path(pasta.name) / "dados.json")


class UsaMySQL:
    def criar_repositorio(self):
        return apoio_mysql.criar_repositorio_mysql()


# --- Classes concretas (são estas que o unittest executa) ---------------------

class TestEmpresaUsuariaEProdutosMemoria(UsaMemoria, ContratoEmpresaUsuariaEProdutos, unittest.TestCase):
    pass


class TestEmpresaUsuariaEProdutosJson(UsaJson, ContratoEmpresaUsuariaEProdutos, unittest.TestCase):
    pass


@apoio_mysql.requer_mysql
class TestPerfisMySQL(UsaMySQL, ContratoPerfis, unittest.TestCase):
    pass


@apoio_mysql.requer_mysql
class TestEmpresasMySQL(UsaMySQL, ContratoEmpresas, unittest.TestCase):
    pass


@apoio_mysql.requer_mysql
class TestProspeccoesMySQL(UsaMySQL, ContratoProspeccoes, unittest.TestCase):

    def setUp(self):
        super().setUp()
        # no banco, prospecção e lead exigem perfil e estabelecimento existentes
        self.repo.salvar_perfil(novo_perfil("P1"))
        self.repo.salvar_perfil(novo_perfil("P2"))
        self.repo.salvar_empresa(nova_empresa())


@apoio_mysql.requer_mysql
class TestEmpresaUsuariaEProdutosMySQL(UsaMySQL, ContratoEmpresaUsuariaEProdutos, unittest.TestCase):
    pass

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

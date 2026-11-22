"""Testes específicos do repositório PostgreSQL e do esquema (BACK-06 / BACK-08).

Os testes de contrato comuns (perfis, empresas, prospecções) ficam em
testes_repositorio.py. Aqui entra o que só existe no banco: transações,
chaves estrangeiras, CHECKs do esquema, substitutos provisórios e falhas.
Precisam de um PostgreSQL de teste (ver tests/apoio_postgres.py).
"""

import unittest
from datetime import datetime

import psycopg2

from src.dominio.empresa import Empresa
from src.dominio.lead import Lead, StatusLead
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao, StatusProspeccao
from src.excecoes import (
    DadosInvalidosError,
    PerfilInvalidoError,
    PerfilNaoEncontradoError,
    PersistenciaError,
    ProspeccaoNaoEncontradaError,
)
from src.persistencia.conexao import GerenciadorConexao
from src.persistencia.repositorio_postgres import (
    EMPRESA_USUARIA_PADRAO_CNPJ,
    RepositorioPostgres,
)
from src.servicos.servico_perfil import ServicoPerfil
from src.servicos.servico_prospeccao import ServicoProspeccao
from tests import apoio_postgres
from tests.apoio_postgres import executar


def perfil(nome="Perfil A", **extra):
    dados = dict(nome=nome, cnaes_desejados=["6204000"], porte_desejado=3,
                 municipio_alvo_ibge="5208707")
    dados.update(extra)
    return Perfil(**dados)


def empresa(cnpj="11111111000111", razao="Empresa A", **extra):
    dados = dict(cnpj=cnpj, razao_social=razao, cnae_principal="6204000",
                 porte=3, municipio_ibge="5208707", cep="75700000")
    dados.update(extra)
    return Empresa(**dados)


def contar(tabela):
    return executar(f"SELECT count(*) FROM {tabela}")[0][0]


@apoio_postgres.requer_postgres
class Base(unittest.TestCase):

    def setUp(self):
        self.repo = apoio_postgres.criar_repositorio_postgres()


class TestPerfisNoBanco(Base):

    def test_usa_a_empresa_usuaria_padrao(self):
        salvo = self.repo.salvar_perfil(perfil())

        dono = executar(
            "SELECT cnpj FROM empresa_usuaria WHERE id = %s",
            (salvo.empresa_usuaria_id,),
        )
        self.assertEqual(dono[0][0], EMPRESA_USUARIA_PADRAO_CNPJ)

    def test_cria_a_empresa_usuaria_padrao_se_o_seed_nao_rodou(self):
        executar("DELETE FROM empresa_usuaria")
        salvo = self.repo.salvar_perfil(perfil())
        self.assertIsNotNone(salvo.empresa_usuaria_id)
        self.assertEqual(contar("empresa_usuaria"), 1)

    def test_empresa_usuaria_informada_no_construtor(self):
        executar("INSERT INTO empresa_usuaria (nome, cnpj, email) "
                 "VALUES ('Cliente', '12345678000199', 'a@b.com')")
        id_ = executar("SELECT id FROM empresa_usuaria WHERE cnpj='12345678000199'")[0][0]
        repo = RepositorioPostgres(apoio_postgres.gerenciador(), empresa_usuaria_id=id_)

        self.assertEqual(repo.salvar_perfil(perfil()).empresa_usuaria_id, id_)

    def test_empresa_usuaria_no_proprio_perfil_vence_o_construtor(self):
        executar("INSERT INTO empresa_usuaria (nome, cnpj, email) "
                 "VALUES ('Outra', '12345678000199', 'o@b.com')")
        id_ = executar("SELECT id FROM empresa_usuaria WHERE cnpj='12345678000199'")[0][0]

        salvo = self.repo.salvar_perfil(perfil(empresa_usuaria_id=id_))
        self.assertEqual(self.repo.buscar_perfil(salvo.id).empresa_usuaria_id, id_)

    def test_atualizar_mantem_o_dono(self):
        executar("INSERT INTO empresa_usuaria (nome, cnpj, email) "
                 "VALUES ('Outra', '12345678000199', 'o@b.com')")
        id_ = executar("SELECT id FROM empresa_usuaria WHERE cnpj='12345678000199'")[0][0]
        salvo = self.repo.salvar_perfil(perfil(empresa_usuaria_id=id_))

        salvo.empresa_usuaria_id = None
        salvo.nome = "Novo nome"
        self.repo.salvar_perfil(salvo)

        self.assertEqual(self.repo.buscar_perfil(salvo.id).empresa_usuaria_id, id_)

    def test_ida_e_volta_de_todos_os_campos(self):
        original = perfil(
            cnaes_desejados=["6204000", "5611201"],
            peso_segmento=33.33, peso_porte=33.33, peso_localizacao=33.34,
            capital_minimo=150000.5,
        )
        salvo = self.repo.salvar_perfil(original)
        lido = self.repo.buscar_perfil(salvo.id)

        self.assertEqual(lido.peso_segmento, 33.33)
        self.assertEqual(lido.peso_localizacao, 33.34)
        self.assertEqual(lido.capital_minimo, 150000.5)
        self.assertEqual(lido.municipio_alvo_ibge, "5208707")
        # os CNAEs voltam ordenados (o esquema não guarda a ordem de cadastro)
        self.assertEqual(sorted(original.cnaes_desejados), lido.cnaes_desejados)
        salvo.cnaes_desejados.sort()
        self.assertEqual(lido, salvo)

    def test_atualizar_troca_os_cnaes(self):
        salvo = self.repo.salvar_perfil(perfil(cnaes_desejados=["6204000", "5611201"]))
        salvo.cnaes_desejados = ["4520001"]
        self.repo.salvar_perfil(salvo)

        self.assertEqual(self.repo.buscar_perfil(salvo.id).cnaes_desejados, ["4520001"])
        self.assertEqual(contar("perfil_cnae"), 1)

    def test_nome_repetido_na_mesma_empresa_usuaria(self):
        self.repo.salvar_perfil(perfil("Igual"))
        with self.assertRaises(PerfilInvalidoError):
            self.repo.salvar_perfil(perfil("Igual"))
        self.assertEqual(contar("perfil_cliente_ideal"), 1)

    def test_falha_nao_atribui_id_nem_grava_nada(self):
        invalido = perfil(cnaes_desejados=["6204000", "9999998"])  # CNAE fora do cadastro

        with self.assertRaises(PersistenciaError) as ctx:
            self.repo.salvar_perfil(invalido)

        self.assertIsNone(invalido.id)
        self.assertIn("9999998", str(ctx.exception))
        self.assertIn("seed_dominios", str(ctx.exception))
        self.assertEqual(contar("perfil_cliente_ideal"), 0)
        self.assertEqual(contar("perfil_cnae"), 0)

    def test_municipio_alvo_fora_do_cadastro(self):
        with self.assertRaises(PersistenciaError):
            self.repo.salvar_perfil(perfil(municipio_alvo_ibge="1100015"))

    def test_atualizar_inexistente_nao_cria(self):
        p = perfil()
        p.id = 7
        with self.assertRaises(PerfilNaoEncontradoError):
            self.repo.salvar_perfil(p)
        self.assertEqual(contar("perfil_cliente_ideal"), 0)

    def test_listar_traz_cada_perfil_com_os_seus_cnaes(self):
        self.repo.salvar_perfil(perfil("A", cnaes_desejados=["6204000"]))
        self.repo.salvar_perfil(perfil("B", cnaes_desejados=["5611201", "4520001"]))

        a, b = self.repo.listar_perfis()
        self.assertEqual(a.cnaes_desejados, ["6204000"])
        self.assertEqual(b.cnaes_desejados, ["4520001", "5611201"])


class TestEmpresasNoBanco(Base):

    def test_distribui_os_dados_pelas_tabelas(self):
        self.repo.salvar_empresa(empresa(
            cnaes_secundarios=["5611201", "4520001"],
            latitude=-16.68, longitude=-49.25,
        ))

        self.assertEqual(contar("empresa"), 1)
        self.assertEqual(contar("estabelecimento"), 1)
        self.assertEqual(contar("cep"), 1)
        self.assertEqual(contar("estabelecimento_cnae_secundario"), 2)

        lida = self.repo.buscar_empresa("11111111000111")
        self.assertEqual(lida.cnaes_secundarios, ["4520001", "5611201"])
        self.assertEqual((lida.latitude, lida.longitude), (-16.68, -49.25))
        self.assertEqual((lida.cep, lida.municipio_ibge), ("75700000", "5208707"))

    def test_filiais_compartilham_a_empresa(self):
        self.repo.salvar_empresas([
            empresa("11111111000111", "Matriz Ltda"),
            empresa("11111111000292", "Matriz Ltda"),
        ])

        self.assertEqual(contar("empresa"), 1)
        self.assertEqual(contar("estabelecimento"), 2)

    def test_cep_formatado_e_normalizado(self):
        self.repo.salvar_empresa(empresa(cep="75700-000"))
        self.assertEqual(self.repo.buscar_empresa("11111111000111").cep, "75700000")

    def test_atualizar_troca_os_secundarios(self):
        self.repo.salvar_empresa(empresa(cnaes_secundarios=["5611201"]))
        self.repo.salvar_empresa(empresa(cnaes_secundarios=["4520001"]))

        self.assertEqual(
            self.repo.buscar_empresa("11111111000111").cnaes_secundarios, ["4520001"]
        )

    def test_atualizar_sem_coordenadas_nao_apaga_as_existentes(self):
        self.repo.salvar_empresa(empresa(latitude=-16.68, longitude=-49.25))
        self.repo.salvar_empresa(empresa())

        lida = self.repo.buscar_empresa("11111111000111")
        self.assertEqual((lida.latitude, lida.longitude), (-16.68, -49.25))

    def test_substitutos_provisorios_na_primeira_gravacao(self):
        self.repo.salvar_empresa(empresa())

        linha = executar(
            """SELECT e.situacao_cod, e.motivo_cod, e.data_inicio_atividade,
                      emp.natureza_juridica_cod, emp.capital_social
                 FROM estabelecimento e JOIN empresa emp USING (cnpj_basico)"""
        )[0]
        self.assertEqual(linha[0], "02")
        self.assertEqual(linha[1], "00")
        self.assertEqual(str(linha[2]), "1900-01-01")
        self.assertEqual(linha[3], "2062")
        self.assertEqual(int(linha[4]), 0)

    def test_dados_reais_ja_carregados_nao_sao_sobrescritos(self):
        self.repo.salvar_empresa(empresa())
        executar("UPDATE estabelecimento SET situacao_cod = '08', "
                 "data_inicio_atividade = '2015-03-10'")
        executar("UPDATE empresa SET capital_social = 50000")

        self.repo.salvar_empresa(empresa(razao="Nome novo"))

        linha = executar(
            """SELECT e.situacao_cod, e.data_inicio_atividade, emp.capital_social,
                      emp.razao_social
                 FROM estabelecimento e JOIN empresa emp USING (cnpj_basico)"""
        )[0]
        self.assertEqual(linha[0], "08")
        self.assertEqual(str(linha[1]), "2015-03-10")
        self.assertEqual(int(linha[2]), 50000)
        self.assertEqual(linha[3], "Nome novo")

    def test_sem_cep_nao_grava(self):
        with self.assertRaises(PersistenciaError) as ctx:
            self.repo.salvar_empresa(empresa(cep=None))
        self.assertIn("CEP", str(ctx.exception))
        self.assertEqual(contar("estabelecimento"), 0)

    def test_cep_invalido_nao_grava(self):
        with self.assertRaises(PersistenciaError):
            self.repo.salvar_empresa(empresa(cep="123"))

    def test_salvar_varias_e_tudo_ou_nada(self):
        boas_e_ruim = [
            empresa("11111111000111"),
            empresa("22222222000122", municipio_ibge="1100015"),  # município sem cadastro
        ]
        with self.assertRaises(PersistenciaError):
            self.repo.salvar_empresas(boas_e_ruim)

        for tabela in ("empresa", "estabelecimento", "cep"):
            with self.subTest(tabela):
                self.assertEqual(contar(tabela), 0)

    def test_cnae_principal_fora_do_cadastro(self):
        with self.assertRaises(PersistenciaError) as ctx:
            self.repo.salvar_empresa(empresa(cnae_principal="9999998"))
        self.assertIn("9999998", str(ctx.exception))

    def test_porte_fora_do_dominio_do_banco(self):
        with self.assertRaises(PersistenciaError):
            self.repo.salvar_empresa(empresa(porte=2))
        self.assertEqual(contar("empresa"), 0)

    def test_estabelecimento_sem_cep_no_banco_nao_cabe_no_dominio(self):
        self.repo.salvar_empresa(empresa())
        executar("UPDATE estabelecimento SET cep = NULL")

        with self.assertRaises(PersistenciaError):
            self.repo.buscar_empresa("11111111000111")


class TestProspeccoesNoBanco(Base):

    def setUp(self):
        super().setUp()
        self.perfil = self.repo.salvar_perfil(perfil())
        self.repo.salvar_empresas([
            empresa("11111111000111", "Empresa A"),
            empresa("22222222000122", "Empresa B"),
            empresa("33333333000133", "Empresa C"),
        ])

    def prospeccao(self, leads, **extra):
        return Prospeccao(perfil_id=self.perfil.id, leads=leads, **extra)

    def test_ida_e_volta_completa(self):
        momento = datetime(2026, 11, 17, 18, 30, 5, 123456)
        original = self.prospeccao(
            [Lead("11111111000111", "x", 87.5, ["mesmo CNAE", "mesmo município"],
                  StatusLead.CONTATADO)],
            total_empresas_avaliadas=3, criada_em=momento,
            status=StatusProspeccao.EM_ANDAMENTO,
        )
        salva = self.repo.salvar_prospeccao(original)
        lida = self.repo.buscar_prospeccao(salva.id)

        self.assertEqual(lida.criada_em, momento)
        self.assertEqual(lida.status, StatusProspeccao.EM_ANDAMENTO)
        self.assertEqual(lida.total_empresas_avaliadas, 3)
        lead = lida.leads[0]
        self.assertEqual(lead.pontuacao, 87.5)
        self.assertEqual(lead.justificativas, ["mesmo CNAE", "mesmo município"])
        self.assertEqual(lead.status, StatusLead.CONTATADO)
        self.assertEqual(lead.razao_social, "Empresa A")  # vem do cadastro

    def test_leads_voltam_por_pontuacao(self):
        salva = self.repo.salvar_prospeccao(self.prospeccao([
            Lead("11111111000111", "", 10), Lead("22222222000122", "", 90),
            Lead("33333333000133", "", 50),
        ]))
        lidos = self.repo.buscar_prospeccao(salva.id).leads
        self.assertEqual([l.pontuacao for l in lidos], [90, 50, 10])

    def test_sem_justificativa_volta_lista_vazia(self):
        salva = self.repo.salvar_prospeccao(
            self.prospeccao([Lead("11111111000111", "", 1)])
        )
        self.assertEqual(self.repo.buscar_prospeccao(salva.id).leads[0].justificativas, [])

    def test_prospeccao_sem_leads(self):
        salva = self.repo.salvar_prospeccao(self.prospeccao([]))
        self.assertEqual(self.repo.buscar_prospeccao(salva.id).leads, [])

    def test_salvar_de_novo_substitui_os_leads(self):
        salva = self.repo.salvar_prospeccao(self.prospeccao([
            Lead("11111111000111", "", 10), Lead("22222222000122", "", 20),
        ]))
        salva.leads = [Lead("33333333000133", "", 30, status=StatusLead.CONVERTIDO)]
        self.repo.salvar_prospeccao(salva)

        lidos = self.repo.buscar_prospeccao(salva.id).leads
        self.assertEqual([l.cnpj for l in lidos], ["33333333000133"])
        self.assertEqual(lidos[0].status, StatusLead.CONVERTIDO)
        self.assertEqual(len(self.repo.listar_prospeccoes()), 1)

    def test_id_explicito_nao_quebra_a_sequencia(self):
        self.repo.salvar_prospeccao(self.prospeccao([], id=10))
        nova = self.repo.salvar_prospeccao(self.prospeccao([]))
        self.assertEqual(nova.id, 11)

    def test_lead_de_cnpj_desconhecido_desfaz_a_prospeccao_inteira(self):
        invalida = self.prospeccao([
            Lead("11111111000111", "", 10), Lead("99999999000199", "", 20),
        ])
        with self.assertRaises(PersistenciaError) as ctx:
            self.repo.salvar_prospeccao(invalida)

        self.assertIn("99999999000199", str(ctx.exception))
        self.assertIsNone(invalida.id)
        self.assertEqual(contar("prospeccao"), 0)
        self.assertEqual(contar("lead"), 0)

    def test_perfil_inexistente(self):
        with self.assertRaises(PersistenciaError):
            self.repo.salvar_prospeccao(Prospeccao(perfil_id=999))

    def test_leads_repetidos_sao_rejeitados(self):
        with self.assertRaises(DadosInvalidosError):
            self.repo.salvar_prospeccao(self.prospeccao([
                Lead("11111111000111", "", 10), Lead("11111111000111", "", 20),
            ]))

    def test_justificativa_com_quebra_de_linha_e_rejeitada(self):
        with self.assertRaises(DadosInvalidosError):
            self.repo.salvar_prospeccao(self.prospeccao([
                Lead("11111111000111", "", 10, ["linha 1\nlinha 2"]),
            ]))
        self.assertEqual(contar("prospeccao"), 0)

    def test_pontuacao_fora_de_0_a_100_e_barrada_pelo_banco(self):
        with self.assertRaises(PersistenciaError):
            self.repo.salvar_prospeccao(
                self.prospeccao([Lead("11111111000111", "", 150)])
            )
        self.assertEqual(contar("prospeccao"), 0)

    def test_buscar_inexistente(self):
        with self.assertRaises(ProspeccaoNaoEncontradaError):
            self.repo.buscar_prospeccao(404)

    def test_view_conta_os_leads(self):
        salva = self.repo.salvar_prospeccao(self.prospeccao(
            [Lead("11111111000111", "", 10), Lead("22222222000122", "", 20)],
            total_empresas_avaliadas=3,
        ))
        self.repo.salvar_prospeccao(self.prospeccao([]))

        linhas = executar(
            "SELECT prospeccao_id, total_leads, total_empresas_avaliadas "
            "FROM vw_prospeccao_resumo ORDER BY prospeccao_id"
        )
        self.assertEqual(linhas, [(salva.id, 2, 3), (salva.id + 1, 0, 0)])


class TestRegrasDoEsquema(Base):
    """CHECKs e chaves do DDL, exercitados direto no SQL."""

    def assertBarra(self, sql, parametros=None, erro=psycopg2.errors.CheckViolation):
        with self.assertRaises(erro):
            executar(sql, parametros)

    def inserir_perfil(self, **campos):
        dados = {
            "empresa_usuaria_id": 1, "nome": "P", "porte_desejado": 3,
            "peso_segmento": 50, "peso_porte": 25, "peso_localizacao": 25,
        }
        dados.update(campos)
        colunas = ", ".join(dados)
        marcadores = ", ".join(["%s"] * len(dados))
        return executar(
            f"INSERT INTO perfil_cliente_ideal ({colunas}) VALUES ({marcadores})",
            list(dados.values()),
        )

    def test_pesos_precisam_somar_100(self):
        self.assertBarra(
            "INSERT INTO perfil_cliente_ideal (empresa_usuaria_id, nome, porte_desejado,"
            " peso_segmento, peso_porte, peso_localizacao) VALUES (1,'P',3,50,25,24)"
        )

    def test_peso_individual_limitado_a_100(self):
        self.assertBarra(
            "INSERT INTO perfil_cliente_ideal (empresa_usuaria_id, nome, porte_desejado,"
            " peso_segmento, peso_porte, peso_localizacao) VALUES (1,'P',3,120,-10,-10)"
        )

    def test_capital_minimo_nao_negativo(self):
        self.assertBarra(
            "INSERT INTO perfil_cliente_ideal (empresa_usuaria_id, nome, porte_desejado,"
            " capital_minimo, peso_segmento, peso_porte, peso_localizacao)"
            " VALUES (1,'P',3,-1,50,25,25)"
        )

    def test_empresa_usuaria_e_obrigatoria_no_perfil(self):
        with self.assertRaises(psycopg2.errors.NotNullViolation):
            self.inserir_perfil(empresa_usuaria_id=None)

    def test_porte_do_perfil_no_dominio_permitido(self):
        with self.assertRaises(psycopg2.errors.CheckViolation):
            self.inserir_perfil(porte_desejado=2)

    def test_status_da_prospeccao(self):
        self.repo.salvar_perfil(perfil())
        with self.assertRaises(psycopg2.errors.CheckViolation):
            executar("INSERT INTO prospeccao (perfil_id, executada_em, status) "
                     "VALUES (1, now(), 'pendente')")

    def test_status_do_lead(self):
        self.repo.salvar_perfil(perfil())
        self.repo.salvar_empresa(empresa())
        self.repo.salvar_prospeccao(Prospeccao(perfil_id=1))
        with self.assertRaises(psycopg2.errors.CheckViolation):
            executar("INSERT INTO lead (prospeccao_id, cnpj, pontuacao, status_contato)"
                     " VALUES (1, '11111111000111', 10, 'perdido')")

    def test_uf_com_duas_letras_maiusculas(self):
        with self.assertRaises(psycopg2.errors.CheckViolation):
            executar("INSERT INTO municipio (codigo_ibge, nome, uf) "
                     "VALUES ('3550308', 'São Paulo', 'sp')")

    def test_codigo_receita_do_municipio_e_unico(self):
        executar("UPDATE municipio SET codigo_receita = '9373' WHERE codigo_ibge = '5208707'")
        with self.assertRaises(psycopg2.errors.UniqueViolation):
            executar("UPDATE municipio SET codigo_receita = '9373' "
                     "WHERE codigo_ibge = '5205109'")

    def test_cep_com_8_digitos_e_coordenadas_validas(self):
        casos = {
            "cep curto": ("1234", None, None),
            "latitude absurda": ("75700000", 91, 0),
            "longitude absurda": ("75700000", 0, 181),
        }
        for nome, (cep, lat, lon) in casos.items():
            with self.subTest(nome):
                with self.assertRaises(psycopg2.errors.CheckViolation):
                    executar("INSERT INTO cep (cep, latitude, longitude, municipio_ibge)"
                             " VALUES (%s, %s, %s, '5208707')", (cep, lat, lon))

    def test_cnpj_basico_tem_que_bater_com_o_cnpj(self):
        self.repo.salvar_empresa(empresa())
        executar("INSERT INTO empresa (cnpj_basico, razao_social, natureza_juridica_cod,"
                 " capital_social, porte_cod) VALUES ('99999999','Outra','2062',0,1)")
        with self.assertRaises(psycopg2.errors.CheckViolation):
            executar("INSERT INTO estabelecimento (cnpj, cnpj_basico, situacao_cod,"
                     " data_situacao, motivo_cod, data_inicio_atividade, cnae_principal)"
                     " VALUES ('11111111000999','99999999','02','2020-01-01','00',"
                     "'2020-01-01','6204000')")

    def test_cnae_secundario_repetido_e_barrado_pela_chave(self):
        self.repo.salvar_empresa(empresa())
        executar("INSERT INTO estabelecimento_cnae_secundario VALUES ('11111111000111','5611201')")
        with self.assertRaises(psycopg2.errors.UniqueViolation):
            executar("INSERT INTO estabelecimento_cnae_secundario "
                     "VALUES ('11111111000111','5611201')")

    def test_produto_de_outra_empresa_usuaria_e_barrado(self):
        """FK composta (produto_id, empresa_usuaria_id) → produto(id, empresa_usuaria_id)."""
        executar("INSERT INTO empresa_usuaria (nome, cnpj, email) "
                 "VALUES ('Outra', '12345678000199', 'o@b.com')")
        executar("INSERT INTO produto (empresa_usuaria_id, nome) VALUES (2, 'Produto da outra')")

        with self.assertRaises(psycopg2.errors.ForeignKeyViolation):
            self.inserir_perfil(empresa_usuaria_id=1, produto_id=1)

    def test_produto_da_mesma_empresa_usuaria_e_aceito_e_o_perfil_geral_tambem(self):
        executar("INSERT INTO produto (empresa_usuaria_id, nome) VALUES (1, 'Meu produto')")
        self.inserir_perfil(nome="Com produto", produto_id=1)
        self.inserir_perfil(nome="Geral", produto_id=None)
        self.assertEqual(contar("perfil_cliente_ideal"), 2)

    def test_nome_de_produto_unico_por_empresa_usuaria(self):
        executar("INSERT INTO produto (empresa_usuaria_id, nome) VALUES (1, 'X')")
        with self.assertRaises(psycopg2.errors.UniqueViolation):
            executar("INSERT INTO produto (empresa_usuaria_id, nome) VALUES (1, 'X')")

    def test_cnpj_e_email_da_empresa_usuaria_unicos(self):
        with self.assertRaises(psycopg2.errors.UniqueViolation):
            executar("INSERT INTO empresa_usuaria (nome, cnpj, email) "
                     "VALUES ('Dup', '00000000000000', 'novo@b.com')")
        with self.assertRaises(psycopg2.errors.UniqueViolation):
            executar("INSERT INTO empresa_usuaria (nome, cnpj, email) "
                     "VALUES ('Dup', '12345678000199', 'padrao@radarlead.invalid')")


class TestFalhasDeConexao(unittest.TestCase):

    def repo_sem_servidor(self):
        ger = GerenciadorConexao("host=127.0.0.1 port=1 dbname=x user=x", connect_timeout=2)
        return RepositorioPostgres(ger)

    def test_toda_operacao_vira_persistencia_error(self):
        repo = self.repo_sem_servidor()
        operacoes = {
            "salvar_perfil": lambda: repo.salvar_perfil(perfil()),
            "buscar_perfil": lambda: repo.buscar_perfil(1),
            "listar_perfis": repo.listar_perfis,
            "salvar_empresa": lambda: repo.salvar_empresa(empresa()),
            "salvar_empresas": lambda: repo.salvar_empresas([empresa()]),
            "buscar_empresa": lambda: repo.buscar_empresa("11111111000111"),
            "listar_empresas": repo.listar_empresas,
            "salvar_prospeccao": lambda: repo.salvar_prospeccao(Prospeccao(perfil_id=1)),
            "buscar_prospeccao": lambda: repo.buscar_prospeccao(1),
            "listar_prospeccoes": repo.listar_prospeccoes,
        }
        for nome, operacao in operacoes.items():
            with self.subTest(nome):
                with self.assertRaises(PersistenciaError):
                    operacao()

    def test_objeto_nao_ganha_id_se_a_conexao_falha(self):
        p = perfil()
        with self.assertRaises(PersistenciaError):
            self.repo_sem_servidor().salvar_perfil(p)
        self.assertIsNone(p.id)

    @apoio_postgres.requer_postgres
    def test_tabelas_ausentes_viram_persistencia_error(self):
        apoio_postgres.preparar_schema()
        ger = GerenciadorConexao(
            apoio_postgres.DSN, options="-c search_path=schema_que_nao_existe"
        )
        with self.assertRaises(PersistenciaError):
            RepositorioPostgres(ger).listar_perfis()


class TestFluxoCompleto(Base):
    """Serviços + repositório PostgreSQL, como a aplicação vai usar."""

    class RecomendadorFalso:
        def recomendar(self, empresas, perfil):
            return [
                {"cnpj": e["cnpj"], "pontuacao": 100 - i * 20,
                 "justificativas": [f"CNAE {e['cnae_principal']}", "mesma cidade"]}
                for i, e in enumerate(empresas)
            ]

    def test_cadastra_perfil_prospecta_e_le_de_volta(self):
        self.repo.salvar_empresas([
            empresa("11111111000111", "Empresa A"),
            empresa("22222222000122", "Empresa B"),
        ])
        perfis = ServicoPerfil(self.repo)
        prospeccoes = ServicoProspeccao(self.repo, self.RecomendadorFalso())

        p = perfis.cadastrar(
            nome="TI em Goiânia", cnaes_desejados=["6204000"], porte_desejado=3,
            municipio_alvo_ibge="5208707", peso_segmento=70, peso_porte=20,
            peso_localizacao=10, capital_minimo=10000,
        )
        resultado = prospeccoes.executar(p.id)

        lida = prospeccoes.buscar(resultado.id)
        self.assertEqual(lida.total_empresas_avaliadas, 2)
        self.assertEqual([l.cnpj for l in lida.leads], ["11111111000111", "22222222000122"])
        self.assertEqual(lida.leads[0].justificativas, ["CNAE 6204000", "mesma cidade"])
        self.assertEqual(lida.status, StatusProspeccao.CONCLUIDA)
        self.assertEqual(prospeccoes.listar(p.id)[0].id, resultado.id)
        self.assertEqual(perfis.buscar(p.id).capital_minimo, 10000)

    def test_prospecta_com_empresas_vindas_de_fonte_externa(self):
        """Caso da BrasilAPI: as empresas ainda não estão no banco.

        O lead tem chave estrangeira para estabelecimento, então o serviço
        precisa gravar a empresa antes de gravar a prospecção.
        """
        nova = Empresa(
            cnpj="11111111000111", razao_social="Vinda da API",
            cnae_principal="6204000", porte=3, municipio_ibge="5205109",
            cep="75700000",
        )
        p = ServicoPerfil(self.repo).cadastrar(
            nome="TI em Catalão", cnaes_desejados=["6204000"], porte_desejado=3,
            municipio_alvo_ibge="5205109",
        )
        prospeccoes = ServicoProspeccao(
            self.repo, self.RecomendadorFalso(), fonte_empresas=lambda perfil: [nova]
        )

        resultado = prospeccoes.executar(p.id)

        lida = prospeccoes.buscar(resultado.id)
        self.assertEqual([l.cnpj for l in lida.leads], ["11111111000111"])
        self.assertEqual(lida.leads[0].razao_social, "Vinda da API")
        self.assertEqual(self.repo.buscar_empresa("11111111000111").cep, "75700000")

    def test_fonte_externa_sem_cep_falha_com_mensagem_clara_e_sem_prospeccao(self):
        sem_cep = Empresa(
            cnpj="11111111000111", razao_social="Sem CEP",
            cnae_principal="6204000", porte=3, municipio_ibge="5205109",
        )
        p = ServicoPerfil(self.repo).cadastrar(
            nome="TI em Catalão", cnaes_desejados=["6204000"], porte_desejado=3,
            municipio_alvo_ibge="5205109",
        )
        prospeccoes = ServicoProspeccao(
            self.repo, self.RecomendadorFalso(), fonte_empresas=lambda perfil: [sem_cep]
        )

        with self.assertRaises(PersistenciaError) as contexto:
            prospeccoes.executar(p.id)

        self.assertIn("CEP", str(contexto.exception))
        self.assertEqual(contar("prospeccao"), 0)

    def test_persiste_entre_instancias_do_repositorio(self):
        self.repo.salvar_perfil(perfil())
        outro = RepositorioPostgres(apoio_postgres.gerenciador())
        self.assertEqual(outro.buscar_perfil(1).nome, "Perfil A")

    def test_alterar_objeto_buscado_nao_muda_o_banco(self):
        self.repo.salvar_empresa(empresa())
        lida = self.repo.buscar_empresa("11111111000111")
        lida.razao_social = "alterada"
        self.assertEqual(self.repo.buscar_empresa("11111111000111").razao_social, "Empresa A")


if __name__ == "__main__":
    unittest.main()

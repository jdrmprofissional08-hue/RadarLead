"""Testes do que é específico do RepositorioJson (arquivo, erros, falhas)."""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from src.dominio.empresa import Empresa
from src.dominio.lead import Lead, StatusLead
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao
from src.excecoes import PersistenciaError
from src.persistencia.repositorio_json import RepositorioJson
from src.servicos.servico_perfil import ServicoPerfil
from src.servicos.servico_prospeccao import ServicoProspeccao

FALHA_AO_SUBSTITUIR = "src.persistencia.repositorio_json.os.replace"


def novo_perfil(nome="Perfil A", **extra):
    return Perfil(
        nome=nome,
        cnaes_desejados=["6204000"],
        porte_desejado=3,
        municipio_alvo_ibge="5208707",
        **extra,
    )


def nova_empresa(cnpj="11111111000111", razao_social="Empresa A", **extra):
    return Empresa(
        cnpj=cnpj,
        razao_social=razao_social,
        cnae_principal="6204000",
        porte=3,
        municipio_ibge="5208707",
        **extra,
    )


class BaseJson(unittest.TestCase):

    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.pasta = Path(pasta.name)
        self.arquivo = self.pasta / "dados.json"

    def abrir(self):
        return RepositorioJson(self.arquivo)

    def escrever(self, conteudo):
        """Escreve um texto (ou um objeto, convertido em JSON) no arquivo."""
        if not isinstance(conteudo, str):
            conteudo = json.dumps(conteudo)
        self.arquivo.write_text(conteudo, encoding="utf-8")

    def arquivos_temporarios(self):
        return list(self.pasta.glob("*.tmp"))


class TestPersistenciaEntreExecucoes(BaseJson):

    def test_dados_sobrevivem_a_uma_nova_instancia(self):
        repo = self.abrir()
        perfil = repo.salvar_perfil(
            novo_perfil(peso_cnae=70, peso_porte=20, peso_localizacao=10)
        )
        empresa = nova_empresa(
            cnaes_secundarios=["4520001"],
            cep="75700000",
            latitude=-18.16,
            longitude=-47.94,
        )
        repo.salvar_empresa(empresa)
        prospeccao = Prospeccao(
            perfil_id=perfil.id,
            leads=[
                Lead("11111111000111", "A", 100, ["CNAE compatível"],
                     StatusLead.CONTATADO),
                Lead("22222222000122", "B", 25.5),
            ],
            total_empresas_avaliadas=2,
            criada_em=datetime(2026, 11, 17, 18, 30, 5, 123456),
        )
        repo.salvar_prospeccao(prospeccao)

        reaberto = self.abrir()

        self.assertEqual(reaberto.listar_perfis(), [perfil])
        self.assertEqual(reaberto.listar_empresas(), [empresa])
        self.assertEqual(reaberto.listar_prospeccoes(), [prospeccao])
        self.assertEqual(
            reaberto.buscar_prospeccao(1).leads[0].status, StatusLead.CONTATADO
        )

    def test_ids_continuam_depois_de_reabrir(self):
        repo = self.abrir()
        repo.salvar_perfil(novo_perfil("A"))
        repo.salvar_perfil(novo_perfil("B"))
        repo.salvar_prospeccao(Prospeccao(perfil_id=1))

        reaberto = self.abrir()

        self.assertEqual(reaberto.salvar_perfil(novo_perfil("C")).id, 3)
        self.assertEqual(reaberto.salvar_prospeccao(Prospeccao(perfil_id=1)).id, 2)

    def test_prospeccao_feita_pelo_servico_sobrevive_a_reabertura(self):
        class RecomendadorFalso:
            def recomendar(self, empresas, perfil):
                return [{"cnpj": e["cnpj"], "razao_social": e["razao_social"],
                         "pontuacao": 50, "justificativas": ["teste"]}
                        for e in empresas]

        repo = self.abrir()
        perfil = ServicoPerfil(repo).cadastrar(
            nome="A", cnaes_desejados=["6204000"], porte_desejado=3,
            municipio_alvo_ibge="5208707",
        )
        repo.salvar_empresa(nova_empresa())
        feita = ServicoProspeccao(repo, RecomendadorFalso()).executar(perfil.id)

        reaberto = self.abrir()
        lida = ServicoProspeccao(reaberto, RecomendadorFalso()).buscar(feita.id)

        self.assertEqual(lida, feita)
        self.assertEqual(lida.leads[0].justificativas, ["teste"])

    def test_atualizacao_persiste(self):
        repo = self.abrir()
        perfil = repo.salvar_perfil(novo_perfil("A"))
        perfil.nome = "A atualizado"
        repo.salvar_perfil(perfil)

        self.assertEqual(self.abrir().buscar_perfil(perfil.id).nome, "A atualizado")

    def test_arquivo_inexistente_comeca_vazio_sem_criar_arquivo(self):
        repo = self.abrir()

        self.assertEqual(repo.listar_perfis(), [])
        self.assertFalse(self.arquivo.exists())

    def test_arquivo_vazio_comeca_vazio(self):
        self.escrever("  \n")
        self.assertEqual(self.abrir().listar_perfis(), [])

    def test_cria_as_pastas_que_faltam(self):
        self.arquivo = self.pasta / "dados" / "json" / "radarlead.json"
        self.abrir().salvar_perfil(novo_perfil())

        self.assertTrue(self.arquivo.exists())

    def test_acentos_ficam_legiveis_no_arquivo(self):
        self.abrir().salvar_empresa(nova_empresa(razao_social="Padaria São João"))

        texto = self.arquivo.read_text(encoding="utf-8")
        self.assertIn("Padaria São João", texto)
        self.assertEqual(
            self.abrir().buscar_empresa("11111111000111").razao_social,
            "Padaria São João",
        )

    def test_arquivo_gravado_e_json_valido_e_sem_temporario(self):
        self.abrir().salvar_perfil(novo_perfil())

        dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
        self.assertEqual(dados["versao"], 1)
        self.assertEqual(len(dados["perfis"]), 1)
        self.assertEqual(self.arquivos_temporarios(), [])


class TestArquivoInvalido(BaseJson):

    def test_json_corrompido_levanta_erro_e_nao_mexe_no_arquivo(self):
        self.escrever('{"versao": 1, "perfis": [')

        with self.assertRaises(PersistenciaError):
            self.abrir()

        self.assertEqual(
            self.arquivo.read_text(encoding="utf-8"), '{"versao": 1, "perfis": ['
        )

    def test_caminho_que_e_uma_pasta(self):
        with self.assertRaises(PersistenciaError):
            RepositorioJson(self.pasta)

    def test_arquivo_com_bytes_invalidos(self):
        self.arquivo.write_bytes(b"\xff\xfe\x00\x80")

        with self.assertRaises(PersistenciaError):
            self.abrir()

    def test_estruturas_invalidas(self):
        perfil_ok = novo_perfil().to_dict() | {"id": 1}
        casos = {
            "raiz e uma lista": [],
            "sem versao": {},
            "versao desconhecida": {"versao": 99},
            "perfis nao e lista": {"versao": 1, "perfis": {}},
            "perfil invalido": {
                "versao": 1,
                "perfis": [{**perfil_ok, "cnaes_desejados": []}],
            },
            "perfil sem id": {
                "versao": 1,
                "perfis": [{**perfil_ok, "id": None}],
            },
            "perfis com id repetido": {
                "versao": 1,
                "perfis": [perfil_ok, perfil_ok],
            },
            "empresa invalida": {
                "versao": 1,
                "empresas": [{"cnpj": "123"}],
            },
            "empresas com cnpj repetido": {
                "versao": 1,
                "empresas": [nova_empresa().to_dict()] * 2,
            },
            "prospeccao com status invalido": {
                "versao": 1,
                "prospeccoes": [{
                    "id": 1,
                    "perfil_id": 1,
                    "criada_em": "2026-11-17T18:00:00",
                    "leads": [{
                        "cnpj": "11111111000111",
                        "pontuacao": 10,
                        "status": "inventado",
                    }],
                }],
            },
            "prospeccao com data invalida": {
                "versao": 1,
                "prospeccoes": [{
                    "id": 1, "perfil_id": 1, "criada_em": "ontem", "leads": [],
                }],
            },
            "contador de ids invalido": {
                "versao": 1, "proximo_id_perfil": "x",
            },
        }

        for nome, conteudo in casos.items():
            with self.subTest(nome):
                self.escrever(conteudo)
                with self.assertRaises(PersistenciaError):
                    self.abrir()

    def test_contador_menor_que_o_maior_id_e_corrigido(self):
        self.escrever({
            "versao": 1,
            "proximo_id_perfil": 1,
            "perfis": [novo_perfil().to_dict() | {"id": 5}],
        })

        self.assertEqual(self.abrir().salvar_perfil(novo_perfil("B")).id, 6)

    def test_arquivo_minimo_e_aceito(self):
        self.escrever({"versao": 1})
        self.assertEqual(self.abrir().listar_perfis(), [])


class TestFalhaDeGravacao(BaseJson):

    def test_falha_ao_gravar_levanta_erro_e_desfaz_a_operacao(self):
        repo = self.abrir()
        perfil = novo_perfil()

        with mock.patch(FALHA_AO_SUBSTITUIR, side_effect=OSError("disco cheio")):
            with self.assertRaises(PersistenciaError):
                repo.salvar_perfil(perfil)

        self.assertEqual(repo.listar_perfis(), [])
        self.assertIsNone(perfil.id)
        self.assertFalse(self.arquivo.exists())
        self.assertEqual(self.arquivos_temporarios(), [])

    def test_falha_mantem_o_arquivo_anterior_intacto(self):
        repo = self.abrir()
        repo.salvar_perfil(novo_perfil("A"))
        antes = self.arquivo.read_text(encoding="utf-8")

        with mock.patch(FALHA_AO_SUBSTITUIR, side_effect=OSError("sem permissão")):
            with self.assertRaises(PersistenciaError):
                repo.salvar_perfil(novo_perfil("B"))

        self.assertEqual(self.arquivo.read_text(encoding="utf-8"), antes)
        self.assertEqual([p.nome for p in self.abrir().listar_perfis()], ["A"])
        self.assertEqual(self.arquivos_temporarios(), [])

    def test_repositorio_continua_usavel_depois_da_falha(self):
        repo = self.abrir()

        with mock.patch(FALHA_AO_SUBSTITUIR, side_effect=OSError("falha")):
            with self.assertRaises(PersistenciaError):
                repo.salvar_perfil(novo_perfil("A"))

        perfil = repo.salvar_perfil(novo_perfil("A"))

        self.assertEqual(perfil.id, 1)  # o id da tentativa que falhou não foi gasto
        self.assertEqual(len(self.abrir().listar_perfis()), 1)

    def test_salvar_varias_empresas_e_tudo_ou_nada(self):
        repo = self.abrir()

        with mock.patch(FALHA_AO_SUBSTITUIR, side_effect=OSError("falha")):
            with self.assertRaises(PersistenciaError):
                repo.salvar_empresas([
                    nova_empresa("11111111000111"),
                    nova_empresa("22222222000122"),
                ])

        self.assertEqual(repo.listar_empresas(), [])

    def test_falha_ao_salvar_prospeccao_devolve_o_id_original(self):
        repo = self.abrir()
        prospeccao = Prospeccao(perfil_id=1)

        with mock.patch(FALHA_AO_SUBSTITUIR, side_effect=OSError("falha")):
            with self.assertRaises(PersistenciaError):
                repo.salvar_prospeccao(prospeccao)

        self.assertIsNone(prospeccao.id)
        self.assertEqual(repo.listar_prospeccoes(), [])

    def test_valor_que_nao_cabe_em_json_e_rejeitado(self):
        repo = self.abrir()
        prospeccao = Prospeccao(
            perfil_id=1,
            leads=[Lead("11111111000111", "A", float("nan"))],
        )

        with self.assertRaises(PersistenciaError):
            repo.salvar_prospeccao(prospeccao)

        self.assertEqual(repo.listar_prospeccoes(), [])
        self.assertFalse(self.arquivo.exists())

    def test_pasta_pai_impossivel_de_criar(self):
        bloqueio = self.pasta / "arquivo_comum.txt"
        bloqueio.write_text("oi", encoding="utf-8")
        repo = RepositorioJson(bloqueio / "dados.json")

        with self.assertRaises(PersistenciaError):
            repo.salvar_perfil(novo_perfil())

        self.assertEqual(repo.listar_perfis(), [])

    def test_perfil_inexistente_nao_regrava_o_arquivo(self):
        from src.excecoes import PerfilNaoEncontradoError

        repo = self.abrir()
        perfil = novo_perfil()
        perfil.id = 42

        with mock.patch(FALHA_AO_SUBSTITUIR) as substituir:
            with self.assertRaises(PerfilNaoEncontradoError):
                repo.salvar_perfil(perfil)

        substituir.assert_not_called()
        self.assertEqual(perfil.id, 42)


if __name__ == "__main__":
    unittest.main()

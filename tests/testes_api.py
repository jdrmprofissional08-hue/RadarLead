"""Testes da API HTTP (Flask), usando o cliente de testes (sem abrir porta)."""

import unittest

from src.api.app import criar_app
from src.api.dados_exemplo import empresas_de_exemplo
from src.api.recomendador_projeto import Fornecedor, RecomendadorDoProjeto
from src.dominio.empresa import Empresa
from src.excecoes import PersistenciaError, RecomendadorError
from src.persistencia.repositorio_memoria import RepositorioMemoria

PEDIDO = {
    "nome": "TI em Goiânia",
    "cnaes_desejados": ["6204000"],
    "porte_desejado": 3,
    "municipio_alvo_ibge": "5208707",
    "peso_cnae": 50,
    "peso_porte": 25,
    "peso_localizacao": 25,
}
ORIGEM = "http://localhost:5173"


class RecomendadorFalso:
    """Pontua pela ordem: 100, 80, 60... e justifica."""

    def __init__(self, erro=None):
        self.erro = erro
        self.chamadas = []

    def recomendar(self, empresas, perfil):
        self.chamadas.append((empresas, perfil))
        if self.erro:
            raise self.erro
        return [
            {"cnpj": e["cnpj"], "pontuacao": 100 - i * 20,
             "justificativas": [f"CNAE {e['cnae_principal']}", "mesma cidade"]}
            for i, e in enumerate(empresas)
        ]


class Base(unittest.TestCase):

    def setUp(self):
        self.repo = RepositorioMemoria()
        self.repo.salvar_empresas(empresas_de_exemplo()[:2])
        self.recomendador = RecomendadorFalso()
        self.app = criar_app(self.repo, self.recomendador)
        self.cliente = self.app.test_client()

    def prospectar(self, **mudancas):
        corpo = {**PEDIDO, **mudancas}
        corpo = {k: v for k, v in corpo.items() if v is not ...}
        return self.cliente.post("/api/prospeccoes", json=corpo)

    def assertErro(self, resposta, status, codigo):
        self.assertEqual(resposta.status_code, status, resposta.get_data(as_text=True))
        erro = resposta.get_json()["erro"]
        self.assertEqual(erro["codigo"], codigo)
        self.assertTrue(erro["mensagem"])


class TestProspectar(Base):

    def test_devolve_leads_com_os_campos_do_contrato(self):
        resposta = self.prospectar()

        self.assertEqual(resposta.status_code, 201)
        corpo = resposta.get_json()
        self.assertEqual(corpo["status"], "concluida")
        self.assertEqual(corpo["total_empresas_avaliadas"], 2)
        self.assertEqual(corpo["total_leads"], 2)
        self.assertEqual(corpo["perfil"]["nome"], "TI em Goiânia")

        primeiro = corpo["leads"][0]
        self.assertEqual(primeiro["cnpj"], "11111111000100")
        self.assertEqual(primeiro["razao_social"], "Alfa Sistemas Demonstração Ltda")
        self.assertEqual(primeiro["pontuacao"], 100)
        self.assertEqual(primeiro["justificativas"], ["CNAE 6204000", "mesma cidade"])
        self.assertEqual(primeiro["cnae_principal"], "6204000")
        self.assertEqual(primeiro["porte"], 3)
        self.assertEqual(primeiro["porte_descricao"], "Empresa de pequeno porte")
        self.assertEqual(primeiro["municipio_ibge"], "5208707")
        self.assertEqual(primeiro["status"], "novo")

    def test_resposta_traz_acentos_legiveis(self):
        texto = self.prospectar().get_data(as_text=True)
        self.assertIn("Demonstração", texto)

    def test_o_recomendador_recebe_os_pesos_do_perfil(self):
        self.prospectar(peso_cnae=70, peso_porte=20, peso_localizacao=10)
        perfil = self.recomendador.chamadas[0][1]
        self.assertEqual(
            (perfil["peso_segmento"], perfil["peso_porte"], perfil["peso_localizacao"]),
            (70, 20, 10),
        )

    def test_aceita_peso_segmento_no_lugar_de_peso_cnae(self):
        resposta = self.prospectar(peso_cnae=..., peso_segmento=50)
        self.assertEqual(resposta.status_code, 201)

    def test_sem_empresas_devolve_lista_vazia_com_sucesso(self):
        vazio = criar_app(RepositorioMemoria(), RecomendadorFalso()).test_client()
        resposta = vazio.post("/api/prospeccoes", json=PEDIDO)

        self.assertEqual(resposta.status_code, 201)
        corpo = resposta.get_json()
        self.assertEqual(corpo["leads"], [])
        self.assertEqual(corpo["total_leads"], 0)
        self.assertEqual(corpo["total_empresas_avaliadas"], 0)

    def test_enviar_o_mesmo_perfil_de_novo_atualiza_em_vez_de_duplicar(self):
        self.prospectar()
        self.prospectar(nome="  ti em goiânia ", peso_cnae=60, peso_porte=20, peso_localizacao=20)

        perfis = self.cliente.get("/api/perfis").get_json()["perfis"]
        self.assertEqual(len(perfis), 1)
        self.assertEqual(perfis[0]["peso_segmento"], 60)
        self.assertEqual(len(self.cliente.get("/api/prospeccoes").get_json()["prospeccoes"]), 2)


class TestValidacao(Base):

    def test_campos_obrigatorios_ausentes(self):
        for campo in ("nome", "cnaes_desejados", "porte_desejado", "municipio_alvo_ibge"):
            with self.subTest(campo):
                resposta = self.prospectar(**{campo: ...})
                self.assertErro(resposta, 400, "dados_invalidos")
                self.assertIn(campo, resposta.get_json()["erro"]["mensagem"])

    def test_pesos_que_nao_somam_100(self):
        self.assertErro(self.prospectar(peso_cnae=50, peso_porte=50, peso_localizacao=50),
                        400, "dados_invalidos")

    def test_valores_de_tipo_errado_viram_400_e_nunca_500(self):
        casos = {
            "cnaes_desejados": "6204000",
            "cnaes_desejados_vazio": [],
            "porte_desejado": "grande",
            "porte_invalido": 2,
            "municipio": 123,
            "nome": "",
            "nome_numero": 5,
            "peso_texto": "muito",
            "cnaes_com_numero": [6204000, None],
        }
        mudancas = {
            "cnaes_desejados": {"cnaes_desejados": "6204000"},
            "cnaes_desejados_vazio": {"cnaes_desejados": []},
            "porte_desejado": {"porte_desejado": "grande"},
            "porte_invalido": {"porte_desejado": 2},
            "municipio": {"municipio_alvo_ibge": 123},
            "nome": {"nome": ""},
            "nome_numero": {"nome": 5},
            "peso_texto": {"peso_cnae": "muito"},
            "cnaes_com_numero": {"cnaes_desejados": [6204000, None]},
        }
        for nome in casos:
            with self.subTest(nome):
                resposta = self.prospectar(**mudancas[nome])
                self.assertEqual(resposta.status_code, 400, resposta.get_data(as_text=True))
                self.assertEqual(resposta.get_json()["erro"]["codigo"], "dados_invalidos")

    def test_corpo_invalido(self):
        for corpo in (b"isto nao e json", b"[1, 2]", b"", b"null"):
            with self.subTest(corpo):
                resposta = self.cliente.post(
                    "/api/prospeccoes", data=corpo, content_type="application/json")
                self.assertErro(resposta, 400, "json_invalido")

    def test_nada_e_salvo_quando_o_perfil_e_invalido(self):
        self.prospectar(porte_desejado=2)
        self.assertEqual(self.cliente.get("/api/perfis").get_json()["perfis"], [])


class TestFalhas(Base):

    def test_falha_do_recomendador(self):
        self.recomendador.erro = RuntimeError("quebrou")
        resposta = self.prospectar()
        self.assertErro(resposta, 502, "falha_na_prospeccao")
        self.assertIn("quebrou", resposta.get_json()["erro"]["mensagem"])

    def test_recomendador_fora_do_contrato(self):
        self.recomendador.recomendar = lambda empresas, perfil: "texto"
        self.assertErro(self.prospectar(), 502, "falha_na_prospeccao")

    def test_falha_no_banco(self):
        def quebrar(*_):
            raise PersistenciaError("banco fora do ar")
        self.repo.salvar_perfil = quebrar
        resposta = self.prospectar()
        self.assertErro(resposta, 503, "banco_indisponivel")

    def test_erro_inesperado_nao_vaza_detalhes(self):
        def quebrar(*_):
            raise KeyError("segredo-interno")
        self.repo.listar_perfis = quebrar
        self.app.testing = False
        self.app.config["PROPAGATE_EXCEPTIONS"] = False
        with self.assertLogs(self.app.logger, "ERROR"):
            resposta = self.prospectar()
        self.assertErro(resposta, 500, "erro_interno")
        self.assertNotIn("segredo-interno", resposta.get_data(as_text=True))

    def test_o_servidor_continua_respondendo_depois_de_um_erro(self):
        self.recomendador.erro = RuntimeError("x")
        self.prospectar()
        self.recomendador.erro = None
        self.assertEqual(self.prospectar(nome="Outro").status_code, 201)


class TestConsultas(Base):

    def test_saude(self):
        self.assertEqual(self.cliente.get("/api/saude").get_json(), {"status": "ok"})

    def test_buscar_prospeccao_com_leads(self):
        criada = self.prospectar().get_json()
        lida = self.cliente.get(f"/api/prospeccoes/{criada['id']}").get_json()
        self.assertEqual(lida["leads"], criada["leads"])
        self.assertEqual(lida["perfil"]["nome"], "TI em Goiânia")

    def test_prospeccao_inexistente(self):
        self.assertErro(self.cliente.get("/api/prospeccoes/999"), 404, "nao_encontrado")

    def test_listar_sem_os_leads_e_filtrar_por_perfil(self):
        a = self.prospectar().get_json()
        self.prospectar(nome="Outro")
        todas = self.cliente.get("/api/prospeccoes").get_json()["prospeccoes"]
        self.assertEqual(len(todas), 2)
        self.assertNotIn("leads", todas[0])
        self.assertEqual(todas[0]["total_leads"], 2)

        so_a = self.cliente.get(f"/api/prospeccoes?perfil_id={a['perfil_id']}").get_json()
        self.assertEqual(len(so_a["prospeccoes"]), 1)

    def test_perfil_id_invalido_no_filtro(self):
        self.assertErro(self.cliente.get("/api/prospeccoes?perfil_id=abc"), 400, "dados_invalidos")

    def test_rota_inexistente_e_metodo_errado_respondem_json(self):
        self.assertErro(self.cliente.get("/api/nada"), 404, "rota_inexistente")
        self.assertErro(self.cliente.delete("/api/prospeccoes"), 405, "metodo_nao_permitido")
        self.assertErro(self.cliente.get("/api/prospeccoes/abc"), 404, "rota_inexistente")


class TestCors(Base):

    def test_origem_do_vite_e_liberada(self):
        for origem in (ORIGEM, "http://127.0.0.1:5173"):
            with self.subTest(origem):
                r = self.cliente.get("/api/saude", headers={"Origin": origem})
                self.assertEqual(r.headers["Access-Control-Allow-Origin"], origem)

    def test_preflight_do_post(self):
        r = self.cliente.options("/api/prospeccoes", headers={
            "Origin": ORIGEM, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"})
        self.assertIn(r.status_code, (200, 204))
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], ORIGEM)
        self.assertIn("POST", r.headers["Access-Control-Allow-Methods"])
        self.assertIn("Content-Type", r.headers["Access-Control-Allow-Headers"])

    def test_erros_tambem_levam_cors(self):
        r = self.cliente.post("/api/prospeccoes", data=b"x", headers={"Origin": ORIGEM})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], ORIGEM)

    def test_origem_desconhecida_nao_e_liberada(self):
        r = self.cliente.get("/api/saude", headers={"Origin": "http://site-estranho.com"})
        self.assertNotIn("Access-Control-Allow-Origin", r.headers)

    def test_sem_origem_nao_ha_cabecalho(self):
        self.assertNotIn("Access-Control-Allow-Origin", self.cliente.get("/api/saude").headers)

    def test_origens_configuraveis(self):
        app = criar_app(self.repo, self.recomendador, ["http://meu-front.local"])
        r = app.test_client().get("/api/saude", headers={"Origin": "http://meu-front.local"})
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://meu-front.local")


class TestPipelineDoJose(unittest.TestCase):
    """Roda de verdade o pipeline (src/Recomendadores); pulado se a pasta não existe."""

    @classmethod
    def setUpClass(cls):
        try:
            import src.Recomendadores.pipeline  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("src/Recomendadores ainda não está no repositório")

    def setUp(self):
        self.repo = RepositorioMemoria()
        self.repo.salvar_empresas(empresas_de_exemplo())
        self.cliente = criar_app(
            self.repo, RecomendadorDoProjeto(Fornecedor())).test_client()

    def test_leads_reais_com_pontuacao_pelos_pesos(self):
        corpo = self.cliente.post("/api/prospeccoes", json=PEDIDO).get_json()

        cnpjs = [l["cnpj"] for l in corpo["leads"]]
        # só CNAE 6204000 e situação ativa; a "Zeta" está baixada (8) e fica de fora
        self.assertEqual(sorted(cnpjs), ["11111111000100", "22222222000100", "33333333000100"])
        pontos = {l["cnpj"]: l["pontuacao"] for l in corpo["leads"]}
        self.assertEqual(pontos["11111111000100"], 100)   # CNAE + porte 3 + Goiânia
        self.assertEqual(pontos["22222222000100"], 75)    # CNAE + Goiânia
        self.assertEqual(pontos["33333333000100"], 50)    # só CNAE
        self.assertEqual(corpo["leads"][0]["cnpj"], "11111111000100")

    def test_pesos_do_perfil_mudam_a_pontuacao(self):
        corpo = self.cliente.post("/api/prospeccoes", json={
            **PEDIDO, "nome": "Pesos novos",
            "peso_cnae": 20, "peso_porte": 70, "peso_localizacao": 10}).get_json()
        pontos = {l["cnpj"]: l["pontuacao"] for l in corpo["leads"]}
        self.assertEqual(pontos["11111111000100"], 100)
        self.assertEqual(pontos["22222222000100"], 30)

    def test_fora_do_raio_ou_sem_correspondencia_devolve_vazio(self):
        pequeno = criar_app(self.repo, RecomendadorDoProjeto(Fornecedor(raio_km=1))).test_client()
        corpo = pequeno.post("/api/prospeccoes", json=PEDIDO).get_json()
        self.assertEqual(corpo["leads"], [])

        outro = self.cliente.post("/api/prospeccoes", json={
            **PEDIDO, "nome": "Sem match", "cnaes_desejados": ["1111111"]}).get_json()
        self.assertEqual(outro["leads"], [])
        self.assertEqual(outro["total_empresas_avaliadas"], 6)


class TestRecomendadorDoProjeto(unittest.TestCase):

    def test_sem_a_pasta_do_jose_o_erro_e_claro(self):
        try:
            import src.Recomendadores.pipeline  # noqa: F401
            self.skipTest("a pasta do José existe aqui")
        except ImportError:
            pass
        with self.assertRaises(RecomendadorError) as ctx:
            RecomendadorDoProjeto().recomendar([], {})
        self.assertIn("Recomendadores", str(ctx.exception))

    def test_configuracao_do_fornecedor_pelo_ambiente(self):
        f = Fornecedor.do_ambiente({"RADARLEAD_FORNECEDOR_LAT": "-10.5",
                                    "RADARLEAD_FORNECEDOR_LON": "-48",
                                    "RADARLEAD_RAIO_KM": "120"})
        self.assertEqual((f.latitude, f.longitude, f.raio_km), (-10.5, -48.0, 120.0))
        self.assertEqual(Fornecedor.do_ambiente({}).raio_km, 350.0)
        with self.assertRaises(RecomendadorError):
            Fornecedor.do_ambiente({"RADARLEAD_RAIO_KM": "muito"})


class TestMontagem(unittest.TestCase):

    def test_monta_app_em_memoria_com_demo(self):
        from src.api.__main__ import montar_app
        app = montar_app(ambiente={}, demo=True)
        self.assertEqual(app.test_client().get("/api/saude").status_code, 200)

    def test_origens_pelo_ambiente(self):
        from src.api.__main__ import montar_app
        app = montar_app(ambiente={"RADARLEAD_CORS_ORIGENS": "http://a.local, http://b.local"})
        r = app.test_client().get("/api/saude", headers={"Origin": "http://b.local"})
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://b.local")

    def test_url_mysql_invalida_falha_com_mensagem(self):
        from src.api.__main__ import montar_app
        from src.excecoes import PersistenciaError
        with self.assertRaises(PersistenciaError):
            montar_app(ambiente={"RADARLEAD_MYSQL_URL": "postgresql://x/y"})


if __name__ == "__main__":
    unittest.main()

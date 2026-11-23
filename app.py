"""Aplicação Flask do RadarLead.

Rotas (contrato completo em docs/contrato_api.md):

    POST /api/prospeccoes        perfil completo -> executa e devolve os leads
    GET  /api/prospeccoes        lista as prospecções (sem os leads)
    GET  /api/prospeccoes/<id>   uma prospecção com os leads
    GET  /api/perfis             lista os perfis
    GET  /api/saude              verificação de que o servidor está de pé

Todo erro volta como JSON: {"erro": {"codigo": "...", "mensagem": "..."}}.

As requisições são atendidas uma por vez (um trava por aplicação): o
repositório compartilha uma única conexão com o banco, que não é segura entre
threads. Para este projeto, isso é suficiente e evita corridas.
"""

from __future__ import annotations

import threading
from typing import Optional

from flask import Flask, g, jsonify, request

from src.dominio.perfil import Perfil
from src.excecoes import (
    DadosInvalidosError,
    RecomendadorError,
    RegistroNaoEncontradoError,
    PersistenciaError,
)
from src.persistencia.repositorio import Repositorio
from src.servicos.servico_perfil import ServicoPerfil
from src.servicos.servico_prospeccao import ServicoProspeccao

ORIGENS_PADRAO = ("http://localhost:5173", "http://127.0.0.1:5173")

CAMPOS_OBRIGATORIOS = ("nome", "cnaes_desejados", "porte_desejado", "municipio_alvo_ibge")

DESCRICAO_PORTE = {
    0: "Não informado",
    1: "Microempresa",
    3: "Empresa de pequeno porte",
    5: "Demais",
}


def criar_app(
    repositorio: Repositorio,
    recomendador,
    origens_permitidas=ORIGENS_PADRAO,
) -> Flask:
    """
    repositorio: qualquer implementação de Repositorio.
    recomendador: objeto com recomendar(empresas, perfil) -> list[dict].
    origens_permitidas: origens do frontend liberadas no CORS ("*" libera todas).
    """
    app = Flask(__name__, static_folder=None)
    app.json.ensure_ascii = False  # acentos legíveis no JSON
    app.json.sort_keys = False

    perfis = ServicoPerfil(repositorio)
    prospeccoes = ServicoProspeccao(repositorio, recomendador)
    trava = threading.RLock()
    origens = tuple(origens_permitidas)

    # --- Trava e CORS ----------------------------------------------------

    @app.before_request
    def _entrar():
        trava.acquire()
        g.trava_adquirida = True

    @app.teardown_request
    def _sair(_erro):
        if g.pop("trava_adquirida", False):
            trava.release()

    @app.after_request
    def _cors(resposta):
        origem = request.headers.get("Origin")
        if origem and ("*" in origens or origem in origens):
            resposta.headers["Access-Control-Allow-Origin"] = origem
            resposta.headers["Vary"] = "Origin"
            resposta.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            resposta.headers["Access-Control-Allow-Headers"] = "Content-Type"
            resposta.headers["Access-Control-Max-Age"] = "600"
        return resposta

    # --- Rotas -----------------------------------------------------------

    @app.get("/api/saude")
    def saude():
        return jsonify({"status": "ok"})

    @app.post("/api/prospeccoes")
    def prospectar():
        dados = _ler_json()
        perfil = _salvar_perfil_do_pedido(dados)
        prospeccao = prospeccoes.executar(perfil.id)
        return jsonify(_detalhar(prospeccao, perfil)), 201

    @app.get("/api/prospeccoes")
    def listar_prospeccoes():
        perfil_id = request.args.get("perfil_id")
        if perfil_id is not None:
            try:
                perfil_id = int(perfil_id)
            except ValueError:
                raise DadosInvalidosError("perfil_id deve ser um número inteiro")
        return jsonify({
            "prospeccoes": [_resumir(p) for p in prospeccoes.listar(perfil_id)]
        })

    @app.get("/api/prospeccoes/<int:prospeccao_id>")
    def buscar_prospeccao(prospeccao_id):
        prospeccao = prospeccoes.buscar(prospeccao_id)
        return jsonify(_detalhar(prospeccao, perfis.buscar(prospeccao.perfil_id)))

    @app.get("/api/perfis")
    def listar_perfis():
        return jsonify({"perfis": [p.to_dict() for p in perfis.listar()]})

    # --- Regras do POST --------------------------------------------------

    def _ler_json() -> dict:
        dados = request.get_json(force=True, silent=True)
        if not isinstance(dados, dict):
            raise _Pedido("json_invalido", "O corpo deve ser um objeto JSON")
        faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in dados]
        if faltando:
            raise DadosInvalidosError(f"Campos obrigatórios ausentes: {', '.join(faltando)}")
        return dados

    def _salvar_perfil_do_pedido(dados: dict) -> Perfil:
        """Cria o perfil ou, se já existir um com o mesmo nome, atualiza.

        O banco só admite um perfil por nome em cada empresa usuária; por isso
        enviar de novo o mesmo perfil (com ajustes) não cria duplicata.
        """
        campos = {
            "nome": dados["nome"],
            "cnaes_desejados": dados["cnaes_desejados"],
            "porte_desejado": dados["porte_desejado"],
            "municipio_alvo_ibge": dados["municipio_alvo_ibge"],
        }
        for chave in ("peso_porte", "peso_localizacao", "capital_minimo"):
            if chave in dados:
                campos[chave] = dados[chave]
        # peso_cnae é o nome do contrato do frontend; peso_segmento, o do banco
        peso = dados.get("peso_cnae", dados.get("peso_segmento"))
        if peso is not None:
            campos["peso_segmento"] = peso

        existente = _perfil_com_nome(campos["nome"])
        if existente is None:
            return perfis.cadastrar(**campos)

        completo = {
            "peso_segmento": existente.peso_segmento,
            "peso_porte": existente.peso_porte,
            "peso_localizacao": existente.peso_localizacao,
            "capital_minimo": existente.capital_minimo,
        }
        completo.update(campos)
        atualizado = Perfil(
            id=existente.id,
            empresa_usuaria_id=existente.empresa_usuaria_id,
            **completo,
        )
        return repositorio.salvar_perfil(atualizado)

    def _perfil_com_nome(nome) -> Optional[Perfil]:
        if not isinstance(nome, str):
            return None
        alvo = nome.strip().casefold()
        for perfil in perfis.listar():
            if perfil.nome.strip().casefold() == alvo:
                return perfil
        return None

    # --- Montagem das respostas -----------------------------------------

    def _resumir(prospeccao) -> dict:
        resumo = prospeccao.to_dict()
        resumo["total_leads"] = len(resumo.pop("leads"))
        return resumo

    def _detalhar(prospeccao, perfil) -> dict:
        corpo = _resumir(prospeccao)
        corpo["perfil"] = perfil.to_dict()
        corpo["leads"] = [_lead(lead) for lead in prospeccao.leads]
        return corpo

    def _lead(lead) -> dict:
        dados = lead.to_dict()
        try:
            empresa = repositorio.buscar_empresa(lead.cnpj)
        except RegistroNaoEncontradoError:
            empresa = None
        if empresa:  # o cadastro é a fonte do nome (o recomendador pode não devolvê-lo)
            dados["razao_social"] = empresa.razao_social
        dados["cnae_principal"] = empresa.cnae_principal if empresa else None
        dados["porte"] = empresa.porte if empresa else None
        dados["porte_descricao"] = (
            DESCRICAO_PORTE.get(empresa.porte) if empresa else None
        )
        dados["municipio_ibge"] = empresa.municipio_ibge if empresa else None
        return dados

    # --- Erros -----------------------------------------------------------

    def _erro(status: int, codigo: str, mensagem: str):
        resposta = jsonify({"erro": {"codigo": codigo, "mensagem": mensagem}})
        resposta.status_code = status
        return resposta

    @app.errorhandler(_Pedido)
    def _pedido_invalido(erro):
        return _erro(400, erro.codigo, str(erro))

    @app.errorhandler(DadosInvalidosError)
    def _dados_invalidos(erro):
        return _erro(400, "dados_invalidos", str(erro))

    @app.errorhandler(RegistroNaoEncontradoError)
    def _nao_encontrado(erro):
        return _erro(404, "nao_encontrado", str(erro))

    @app.errorhandler(RecomendadorError)
    def _falha_na_prospeccao(erro):
        return _erro(502, "falha_na_prospeccao", str(erro))

    @app.errorhandler(PersistenciaError)
    def _falha_no_banco(erro):
        return _erro(503, "banco_indisponivel", str(erro))

    @app.errorhandler(404)
    def _rota_inexistente(_erro_http):
        return _erro(404, "rota_inexistente", "Rota não encontrada")

    @app.errorhandler(405)
    def _metodo_nao_permitido(_erro_http):
        return _erro(405, "metodo_nao_permitido", "Método HTTP não permitido nesta rota")

    @app.errorhandler(Exception)
    def _erro_inesperado(erro):
        app.logger.exception("Erro inesperado: %s", erro)
        return _erro(500, "erro_interno", "Erro interno do servidor")

    return app


class _Pedido(Exception):
    """Pedido malformado (antes mesmo de chegar ao domínio)."""

    def __init__(self, codigo: str, mensagem: str):
        super().__init__(mensagem)
        self.codigo = codigo

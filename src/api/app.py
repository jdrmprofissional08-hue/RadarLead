"""Aplicação Flask do RadarLead.

Rotas (contrato completo em docs/contrato_api.md):

    POST /api/prospeccoes        perfil completo -> executa e devolve os leads
    GET/PUT /api/empresa-usuaria a empresa atual (modo demonstração: uma só)
    GET/POST /api/produtos       produtos da empresa atual
    GET  /api/produtos/<id>      um produto
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

import math
import threading
from typing import Optional

from flask import Flask, g, jsonify, request

from src.api.recomendador_projeto import RAIO_KM_MAXIMO
from src.dominio import validacao
from src.dominio.empresa_usuaria import EmpresaUsuaria, Produto
from src.dominio.perfil import Perfil
from src.excecoes import (
    DadosInvalidosError,
    DuplicadoError,
    EmpresaUsuariaNaoEncontradaError,
    PersistenciaError,
    ProdutoNaoEncontradoError,
    ProspeccaoNaoEncontradaError,
    RadarLeadError,
    RecomendadorError,
    ReferenciaInexistenteError,
    RegistroNaoEncontradoError,
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
            resposta.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
            resposta.headers["Access-Control-Allow-Headers"] = "Content-Type"
            resposta.headers["Access-Control-Max-Age"] = "600"
        return resposta

    # --- Rotas -----------------------------------------------------------

    @app.get("/api/saude")
    def saude():
        try:
            cadastrada = repositorio.buscar_empresa_usuaria_atual() is not None
        except EmpresaUsuariaNaoEncontradaError:
            cadastrada = False
        except RadarLeadError:
            cadastrada = None  # não deu para consultar; o servidor está de pé mesmo assim
        return jsonify({
            "status": "ok",
            "modo": "demonstracao",  # uma empresa usuária só, sem login
            "empresa_usuaria_cadastrada": cadastrada,
        })

    # --- Empresa usuária (a "atual") ---------------------------------------

    @app.get("/api/empresa-usuaria")
    def buscar_empresa_usuaria():
        return jsonify(repositorio.buscar_empresa_usuaria_atual().to_dict())

    @app.put("/api/empresa-usuaria")
    def salvar_empresa_usuaria():
        dados = _ler_objeto()
        _exigir_campos(dados, ("nome", "cnpj", "email"))
        nova = EmpresaUsuaria(nome=dados["nome"], cnpj=dados["cnpj"], email=dados["email"])
        try:
            repositorio.buscar_empresa_usuaria_atual()
            existia = True
        except EmpresaUsuariaNaoEncontradaError:
            existia = False
        salva = repositorio.salvar_empresa_usuaria_atual(nova)
        return jsonify(salva.to_dict()), (200 if existia else 201)

    # --- Produtos ----------------------------------------------------------

    @app.get("/api/produtos")
    def listar_produtos():
        empresa = repositorio.buscar_empresa_usuaria_atual()
        produtos = repositorio.listar_produtos(empresa.id)
        return jsonify({"produtos": [p.to_dict() for p in produtos]})

    @app.post("/api/produtos")
    def criar_produto():
        empresa = repositorio.buscar_empresa_usuaria_atual()
        dados = _ler_objeto()
        _exigir_campos(dados, ("nome",))
        produto = Produto(nome=dados["nome"], descricao=dados.get("descricao"),
                          empresa_usuaria_id=empresa.id)
        return jsonify(repositorio.salvar_produto(produto).to_dict()), 201

    @app.get("/api/produtos/<int:produto_id>")
    def buscar_produto(produto_id):
        empresa = repositorio.buscar_empresa_usuaria_atual()
        return jsonify(repositorio.buscar_produto(produto_id, empresa.id).to_dict())

    # --- Prospecção --------------------------------------------------------

    @app.post("/api/prospeccoes")
    def prospectar():
        dados = _ler_objeto()
        _exigir_campos(dados, CAMPOS_OBRIGATORIOS)
        origem = _ler_origem(dados)
        perfil = _salvar_perfil_do_pedido(dados)

        servico = prospeccoes
        if origem:
            com_origem = getattr(recomendador, "com_origem", None)
            if com_origem is None:
                raise RecomendadorError("Este recomendador não aceita origem personalizada")
            servico = ServicoProspeccao(
                repositorio,
                com_origem(origem["latitude"], origem["longitude"], origem["raio_km"]),
            )

        prospeccao = servico.executar(perfil.id)
        corpo = _detalhar(prospeccao, perfil)
        if origem:
            # só para conferência: a origem vale para esta execução e não é gravada
            raio = origem["raio_km"]
            if raio is None:
                raio = getattr(getattr(servico, "_recomendador", None), "fornecedor", None)
                raio = getattr(raio, "raio_km", None)
            corpo["origem"] = {"latitude": origem["latitude"],
                               "longitude": origem["longitude"], "raio_km": raio}
        return jsonify(corpo), 201

    @app.get("/api/prospeccoes")
    def listar_prospeccoes():
        meus = {p.id for p in _perfis_da_empresa()}
        perfil_id = request.args.get("perfil_id")
        if perfil_id is not None:
            try:
                perfil_id = int(perfil_id)
            except ValueError:
                raise DadosInvalidosError("perfil_id deve ser um número inteiro")
            if perfil_id not in meus:
                return jsonify({"prospeccoes": []})
        return jsonify({
            "prospeccoes": [
                _resumir(p) for p in prospeccoes.listar(perfil_id) if p.perfil_id in meus
            ]
        })

    @app.get("/api/prospeccoes/<int:prospeccao_id>")
    def buscar_prospeccao(prospeccao_id):
        prospeccao = prospeccoes.buscar(prospeccao_id)
        perfil = perfis.buscar(prospeccao.perfil_id)
        if perfil.empresa_usuaria_id != repositorio.empresa_usuaria_atual_id():
            # prospecção de outra empresa: para quem pergunta, ela não existe
            raise ProspeccaoNaoEncontradaError(f"Prospecção {prospeccao_id} não encontrada")
        return jsonify(_detalhar(prospeccao, perfil))

    @app.get("/api/perfis")
    def listar_perfis():
        return jsonify({"perfis": [p.to_dict() for p in _perfis_da_empresa()]})

    # --- Leitura do pedido -------------------------------------------------

    def _ler_objeto() -> dict:
        dados = request.get_json(force=True, silent=True)
        if not isinstance(dados, dict):
            raise _Pedido("json_invalido", "O corpo deve ser um objeto JSON")
        return dados

    def _exigir_campos(dados: dict, campos) -> None:
        faltando = [c for c in campos if c not in dados]
        if faltando:
            raise DadosInvalidosError(f"Campos obrigatórios ausentes: {', '.join(faltando)}")

    def _numero(dados: dict, chave: str, rotulo: str, minimo, maximo,
                exclusivo_minimo: bool = False):
        valor = dados.get(chave)
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) \
                or not math.isfinite(valor):
            raise DadosInvalidosError(f"{rotulo} deve ser um número, recebido: {valor!r}")
        abaixo = valor <= minimo if exclusivo_minimo else valor < minimo
        if abaixo or valor > maximo:
            raise DadosInvalidosError(
                f"{rotulo} fora do intervalo permitido "
                f"({'>' if exclusivo_minimo else '>='} {minimo} e <= {maximo}), "
                f"recebido: {valor!r}"
            )
        return valor

    def _ler_origem(dados: dict) -> Optional[dict]:
        """Origem opcional da busca (vale só para esta execução)."""
        bruta = dados.get("origem")
        if bruta is None:
            return None
        if not isinstance(bruta, dict):
            raise DadosInvalidosError("origem deve ser um objeto com latitude e longitude")
        _exigir_campos(bruta, ("latitude", "longitude"))
        return {
            "latitude": _numero(bruta, "latitude", "Latitude da origem", -90, 90),
            "longitude": _numero(bruta, "longitude", "Longitude da origem", -180, 180),
            "raio_km": (
                _numero(bruta, "raio_km", "Raio da origem (km)", 0, RAIO_KM_MAXIMO,
                        exclusivo_minimo=True)
                if bruta.get("raio_km") is not None else None
            ),
        }

    def _produto_do_pedido(dados: dict):
        """(informado, produto_id). Ausente preserva; número associa; null remove."""
        if "produto_id" not in dados:
            return False, None
        produto_id = dados["produto_id"]
        if produto_id is None:
            return True, None
        if isinstance(produto_id, bool) or not isinstance(produto_id, int):
            raise DadosInvalidosError(
                f"produto_id deve ser um número inteiro ou null, recebido: {produto_id!r}"
            )
        try:
            empresa = repositorio.buscar_empresa_usuaria_atual()
            repositorio.buscar_produto(produto_id, empresa.id)
        except EmpresaUsuariaNaoEncontradaError:
            raise DadosInvalidosError(
                "Cadastre a empresa usuária antes de associar um produto"
            )
        except ProdutoNaoEncontradoError:
            raise DadosInvalidosError(
                f"Produto {produto_id} não encontrado para a empresa atual"
            )
        return True, produto_id

    def _perfis_da_empresa() -> list:
        """Só os perfis da empresa atual (os de outra empresa nunca aparecem)."""
        atual = repositorio.empresa_usuaria_atual_id()
        if atual is None:
            return []
        return [p for p in perfis.listar() if p.empresa_usuaria_id == atual]

    def _salvar_perfil_do_pedido(dados: dict) -> Perfil:
        """Cria o perfil ou, se a empresa já tiver um com o mesmo nome, atualiza.

        Nomes são comparados sem espaços nas pontas, sem acentos e sem
        maiúsculas (como o banco faz). O banco só admite um perfil por nome em
        cada empresa usuária; por isso enviar de novo o mesmo perfil, com
        ajustes, não cria duplicata.
        """
        produto_informado, produto_id = _produto_do_pedido(dados)

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
            return perfis.cadastrar(**campos, produto_id=produto_id)

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
            produto_id=produto_id if produto_informado else existente.produto_id,
            **completo,
        )
        return repositorio.salvar_perfil(atualizado)

    def _perfil_com_nome(nome) -> Optional[Perfil]:
        if not isinstance(nome, str):
            return None
        alvo = validacao.chave_de_nome(nome)
        for perfil in _perfis_da_empresa():
            if validacao.chave_de_nome(perfil.nome) == alvo:
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

    @app.errorhandler(DuplicadoError)
    def _duplicado(erro):
        return _erro(409, "duplicado", str(erro))

    @app.errorhandler(RegistroNaoEncontradoError)
    def _nao_encontrado(erro):
        return _erro(404, "nao_encontrado", str(erro))

    @app.errorhandler(RecomendadorError)
    def _falha_na_prospeccao(erro):
        return _erro(502, "falha_na_prospeccao", str(erro))

    @app.errorhandler(ReferenciaInexistenteError)
    def _referencia_inexistente(erro):
        # o código está certo, mas o catálogo do banco (municípios, CNAEs) não o
        # tem: o banco está no ar, então não é 503
        return _erro(422, "referencia_inexistente", str(erro))

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

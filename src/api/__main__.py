"""Inicia o servidor de desenvolvimento:  python -m src.api

Opções:
    --host 127.0.0.1    --porta 8000
    --demo              carrega empresas fictícias (ver dados_exemplo.py)

Variáveis de ambiente (todas opcionais):
    RADARLEAD_MYSQL_URL        mysql://usuario:senha@localhost:3306/radarlead
                               (sem ela, os dados ficam em memória e somem ao parar)
    RADARLEAD_EMPRESA_USUARIA_ID  id da empresa usuária "atual" (padrão: a primeira do banco)
    RADARLEAD_CORS_ORIGENS     origens liberadas, separadas por vírgula
                               (padrão: http://localhost:5173,http://127.0.0.1:5173)
    RADARLEAD_FORNECEDOR_LAT / RADARLEAD_FORNECEDOR_LON / RADARLEAD_RAIO_KM
                               ponto de origem e raio (km, máx. 350) da busca
"""

from __future__ import annotations

import argparse
import os
import sys

from src.api.app import ORIGENS_PADRAO, criar_app
from src.api.dados_exemplo import empresas_de_exemplo
from src.api.recomendador_projeto import Fornecedor, RecomendadorDoProjeto
from src.excecoes import PersistenciaError, RadarLeadError


def montar_repositorio(ambiente=None):
    ambiente = os.environ if ambiente is None else ambiente
    url = ambiente.get("RADARLEAD_MYSQL_URL")
    if url:
        from src.persistencia.conexao_mysql import GerenciadorConexaoMySQL
        from src.persistencia.repositorio_mysql import RepositorioMySQL

        empresa = ambiente.get("RADARLEAD_EMPRESA_USUARIA_ID")
        try:
            empresa_id = int(empresa) if empresa else None
        except ValueError:
            raise PersistenciaError(
                f"RADARLEAD_EMPRESA_USUARIA_ID deve ser um número inteiro, recebido: {empresa!r}"
            )
        return RepositorioMySQL(GerenciadorConexaoMySQL(url), empresa_usuaria_id=empresa_id)

    from src.persistencia.repositorio_memoria import RepositorioMemoria

    return RepositorioMemoria()


def montar_app(ambiente=None, demo: bool = False):
    ambiente = os.environ if ambiente is None else ambiente
    repositorio = montar_repositorio(ambiente)
    if demo:
        repositorio.salvar_empresas(empresas_de_exemplo())

    origens = ambiente.get("RADARLEAD_CORS_ORIGENS")
    origens = tuple(o.strip() for o in origens.split(",") if o.strip()) if origens else ORIGENS_PADRAO

    recomendador = RecomendadorDoProjeto(Fornecedor.do_ambiente(ambiente))
    return criar_app(repositorio, recomendador, origens)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--demo", action="store_true",
                        help="carrega empresas fictícias para teste")
    argumentos = parser.parse_args(argv)

    try:
        app = montar_app(demo=argumentos.demo)
    except RadarLeadError as erro:
        print(f"Não foi possível iniciar: {erro}", file=sys.stderr)
        return 1

    print(f"RadarLead API em http://{argumentos.host}:{argumentos.porta}/api/saude")
    app.run(host=argumentos.host, port=argumentos.porta, threaded=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

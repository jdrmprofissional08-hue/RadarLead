"""Serviço de prospecção (BACK-03 e BACK-04).

Fluxo de executar(perfil_id):
    1. busca o perfil no repositório;
    2. obtém as empresas (do repositório, ou de uma fonte externa);
    3. chama o recomendador;
    4. converte as recomendações em Leads;
    5. salva e devolve a Prospeccao.
"""

from typing import Callable, Optional

from src.dominio.empresa import Empresa
from src.dominio.lead import Lead
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao
from src.excecoes import DadosInvalidosError, RadarLeadError, RecomendadorError
from src.persistencia.repositorio import Repositorio


class ServicoProspeccao:
    """
    recomendador: qualquer objeto com recomendar(empresas: list[dict],
        perfil: dict) -> list[dict] (contrato da classe Recomendador).
    fonte_empresas: opcional. Função que recebe o Perfil e devolve uma
        lista de Empresa. Será usada para plugar a BrasilAPI depois; sem
        ela, usa as empresas guardadas no repositório.
    """

    def __init__(
        self,
        repositorio: Repositorio,
        recomendador,
        fonte_empresas: Optional[Callable[[Perfil], list[Empresa]]] = None,
    ):
        self._repositorio = repositorio
        self._recomendador = recomendador
        self._fonte_empresas = fonte_empresas

    def executar(self, perfil_id: int) -> Prospeccao:
        perfil = self._repositorio.buscar_perfil(perfil_id)
        empresas = self._obter_empresas(perfil)
        recomendacoes = self._recomendar(empresas, perfil)
        leads = self._criar_leads(recomendacoes)

        prospeccao = Prospeccao(
            perfil_id=perfil.id,
            leads=leads,
            total_empresas_avaliadas=len(empresas),
        )
        return self._repositorio.salvar_prospeccao(prospeccao)

    def buscar(self, prospeccao_id: int) -> Prospeccao:
        """Levanta ProspeccaoNaoEncontradaError se o id não existir."""
        return self._repositorio.buscar_prospeccao(prospeccao_id)

    def listar(self, perfil_id: Optional[int] = None) -> list[Prospeccao]:
        return self._repositorio.listar_prospeccoes(perfil_id)

    # --- passos internos -----------------------------------------------

    def _obter_empresas(self, perfil: Perfil) -> list[Empresa]:
        if self._fonte_empresas is not None:
            return list(self._fonte_empresas(perfil))

        return self._repositorio.listar_empresas()

    def _recomendar(self, empresas: list[Empresa], perfil: Perfil) -> list:
        try:
            resultado = self._recomendador.recomendar(
                [e.to_dict() for e in empresas], perfil.to_dict()
            )
        except RadarLeadError:
            raise
        except Exception as erro:
            raise RecomendadorError(
                f"O recomendador falhou: {erro}"
            ) from erro

        if not isinstance(resultado, list):
            raise RecomendadorError(
                "O recomendador deve devolver uma lista, "
                f"mas devolveu {type(resultado).__name__}"
            )

        return resultado

    @staticmethod
    def _criar_leads(recomendacoes: list) -> list[Lead]:
        try:
            leads = [Lead.de_recomendacao(item) for item in recomendacoes]
        except DadosInvalidosError as erro:
            raise RecomendadorError(
                f"Resposta do recomendador fora do contrato: {erro}"
            ) from erro

        # maior pontuação primeiro; empates mantêm a ordem do recomendador
        leads.sort(key=lambda lead: lead.pontuacao, reverse=True)
        return leads

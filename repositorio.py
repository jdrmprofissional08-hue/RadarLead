"""Interface comum de persistência.

Os serviços dependem só desta classe. Assim dá para trocar a implementação
(memória, JSON, PostgreSQL) sem mexer na lógica de negócio.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.empresa import Empresa
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao


class Repositorio(ABC):

    # --- Perfis ------------------------------------------------------------

    @abstractmethod
    def salvar_perfil(self, perfil: Perfil) -> Perfil:
        """Grava o perfil. Sem id: cria e atribui um id. Com id: atualiza.

        Levanta PerfilNaoEncontradoError se o id informado não existir.
        """

    @abstractmethod
    def buscar_perfil(self, perfil_id: int) -> Perfil:
        """Devolve o perfil ou levanta PerfilNaoEncontradoError."""

    @abstractmethod
    def listar_perfis(self) -> list[Perfil]:
        """Todos os perfis, em ordem de cadastro."""

    # --- Empresas ----------------------------------------------------------

    @abstractmethod
    def salvar_empresa(self, empresa: Empresa) -> Empresa:
        """Cria ou atualiza a empresa (a chave é o CNPJ)."""

    @abstractmethod
    def salvar_empresas(self, empresas: list[Empresa]) -> list[Empresa]:
        """Cria ou atualiza várias empresas de uma vez."""

    @abstractmethod
    def buscar_empresa(self, cnpj: str) -> Empresa:
        """Devolve a empresa ou levanta EmpresaNaoEncontradaError."""

    @abstractmethod
    def listar_empresas(self) -> list[Empresa]:
        """Todas as empresas, em ordem de inserção."""

    # --- Prospecções -------------------------------------------------------

    @abstractmethod
    def salvar_prospeccao(self, prospeccao: Prospeccao) -> Prospeccao:
        """Grava a prospecção (e seus leads) e atribui um id se não houver."""

    @abstractmethod
    def buscar_prospeccao(self, prospeccao_id: int) -> Prospeccao:
        """Devolve a prospecção ou levanta ProspeccaoNaoEncontradaError."""

    @abstractmethod
    def listar_prospeccoes(
        self, perfil_id: Optional[int] = None
    ) -> list[Prospeccao]:
        """Todas as prospecções, ou só as de um perfil se perfil_id for dado."""

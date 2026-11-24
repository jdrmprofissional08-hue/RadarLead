"""Interface comum de persistência.

Os serviços dependem só desta classe. Assim dá para trocar a implementação
(memória, JSON, PostgreSQL) sem mexer na lógica de negócio.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.empresa import Empresa
from src.dominio.empresa_usuaria import EmpresaUsuaria, Produto
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao
from src.excecoes import PersistenciaError


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

    # --- Empresa usuária e produtos ---------------------------------------
    #
    # Modo demonstração: existe UMA empresa usuária "atual" (a primeira do
    # banco, ou a configurada na criação do repositório). Perfis e produtos
    # pertencem a ela. Não há login: isto organiza os dados, mas não isola
    # usuários diferentes entre si.
    #
    # Não são abstratos: um repositório que não os implementa responde com
    # PersistenciaError, em vez de impedir o uso do resto.

    def empresa_usuaria_atual_id(self) -> Optional[int]:
        """Id da empresa atual (mesmo a provisória) ou None se não houver nenhuma."""
        raise self._sem_suporte("empresa usuária")

    def buscar_empresa_usuaria_atual(self) -> EmpresaUsuaria:
        """A empresa atual, ou EmpresaUsuariaNaoEncontradaError se ainda não
        foi cadastrada (a empresa provisória não conta como cadastro)."""
        raise self._sem_suporte("empresa usuária")

    def salvar_empresa_usuaria_atual(self, empresa: EmpresaUsuaria) -> EmpresaUsuaria:
        """Cadastra a empresa atual ou atualiza os dados dela.

        Levanta DuplicadoError se o CNPJ ou o e-mail já pertencem a outra empresa.
        """
        raise self._sem_suporte("empresa usuária")

    def salvar_produto(self, produto: Produto) -> Produto:
        """Cria (sem id) ou atualiza o produto da empresa em produto.empresa_usuaria_id.

        Levanta DuplicadoError se a empresa já tem produto com esse nome
        (ignorando maiúsculas e acentos).
        """
        raise self._sem_suporte("produtos")

    def buscar_produto(self, produto_id: int, empresa_usuaria_id: int) -> Produto:
        """Levanta ProdutoNaoEncontradoError se não existir ou for de outra empresa."""
        raise self._sem_suporte("produtos")

    def listar_produtos(self, empresa_usuaria_id: int) -> list[Produto]:
        """Produtos da empresa, em ordem de cadastro."""
        raise self._sem_suporte("produtos")

    @staticmethod
    def _sem_suporte(recurso: str) -> PersistenciaError:
        return PersistenciaError(
            f"Este repositório não suporta {recurso} (use memória, JSON ou MySQL)"
        )

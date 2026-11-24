"""Repositório em memória: serve para desenvolver e testar sem banco.

Os dados guardados são cópias. Alterar um objeto depois de salvá-lo, ou o
objeto devolvido por uma busca, não muda o que está guardado: só salvar de
novo muda. É o mesmo comportamento que o JSON e o PostgreSQL terão.
"""

from copy import deepcopy
from typing import Optional

from src.dominio import validacao
from src.dominio.empresa import Empresa
from src.dominio.empresa_usuaria import EmpresaUsuaria, Produto
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
from src.persistencia.marcadores import (
    EMPRESA_USUARIA_PADRAO_CNPJ,
    EMPRESA_USUARIA_PADRAO_EMAIL,
    EMPRESA_USUARIA_PADRAO_NOME,
)
from src.persistencia.repositorio import Repositorio


class RepositorioMemoria(Repositorio):

    def __init__(self):
        self._perfis: dict[int, Perfil] = {}
        self._empresas: dict[str, Empresa] = {}
        self._prospeccoes: dict[int, Prospeccao] = {}
        self._empresas_usuarias: dict[int, EmpresaUsuaria] = {}
        self._produtos: dict[int, Produto] = {}
        self._proximo_id_perfil = 1
        self._proximo_id_prospeccao = 1
        self._proximo_id_empresa_usuaria = 1
        self._proximo_id_produto = 1

    # --- Perfis ------------------------------------------------------------

    def salvar_perfil(self, perfil: Perfil) -> Perfil:
        if perfil.id is not None and perfil.id not in self._perfis:
            raise PerfilNaoEncontradoError(
                f"Perfil {perfil.id} não existe e não pode ser atualizado"
            )

        # sem dono informado: atualização mantém o dono atual; perfil novo vai
        # para a empresa atual (a provisória é criada se ainda não houver nenhuma)
        dono = perfil.empresa_usuaria_id
        if dono is None and perfil.id is not None:
            dono = self._perfis[perfil.id].empresa_usuaria_id
        if dono is None:
            dono = self._empresa_atual_ou_provisoria().id

        if perfil.produto_id is not None:
            produto = self._produtos.get(perfil.produto_id)
            if produto is None or produto.empresa_usuaria_id != dono:
                raise DadosInvalidosError(
                    f"Produto {perfil.produto_id} não existe para a empresa do perfil"
                )

        if perfil.id is None:
            perfil.id = self._proximo_id_perfil
            self._proximo_id_perfil += 1
        perfil.empresa_usuaria_id = dono

        self._perfis[perfil.id] = deepcopy(perfil)
        return perfil

    def buscar_perfil(self, perfil_id: int) -> Perfil:
        if perfil_id not in self._perfis:
            raise PerfilNaoEncontradoError(f"Perfil {perfil_id} não encontrado")

        return deepcopy(self._perfis[perfil_id])

    def listar_perfis(self) -> list[Perfil]:
        return [deepcopy(p) for p in self._perfis.values()]

    # --- Empresas ----------------------------------------------------------

    def salvar_empresa(self, empresa: Empresa) -> Empresa:
        self._empresas[empresa.cnpj] = deepcopy(empresa)
        return empresa

    def salvar_empresas(self, empresas: list[Empresa]) -> list[Empresa]:
        # chama a versão desta classe de propósito: subclasses (como a do JSON)
        # podem gravar em disco em salvar_empresa, e aqui queremos uma gravação só
        return [RepositorioMemoria.salvar_empresa(self, e) for e in empresas]

    def buscar_empresa(self, cnpj: str) -> Empresa:
        if cnpj not in self._empresas:
            raise EmpresaNaoEncontradaError(f"Empresa {cnpj} não encontrada")

        return deepcopy(self._empresas[cnpj])

    def listar_empresas(self) -> list[Empresa]:
        return [deepcopy(e) for e in self._empresas.values()]

    # --- Empresa usuária e produtos ---------------------------------------

    def _empresa_atual(self) -> Optional[EmpresaUsuaria]:
        if not self._empresas_usuarias:
            return None
        return self._empresas_usuarias[min(self._empresas_usuarias)]

    def _empresa_atual_ou_provisoria(self) -> EmpresaUsuaria:
        atual = self._empresa_atual()
        if atual is None:
            atual = EmpresaUsuaria(
                nome=EMPRESA_USUARIA_PADRAO_NOME,
                cnpj=EMPRESA_USUARIA_PADRAO_CNPJ,
                email=EMPRESA_USUARIA_PADRAO_EMAIL,
                id=self._proximo_id_empresa_usuaria,
            )
            self._proximo_id_empresa_usuaria += 1
            self._empresas_usuarias[atual.id] = atual
        return atual

    def empresa_usuaria_atual_id(self) -> Optional[int]:
        atual = self._empresa_atual()
        return None if atual is None else atual.id

    def buscar_empresa_usuaria_atual(self) -> EmpresaUsuaria:
        atual = self._empresa_atual()
        if atual is None or atual.cnpj == EMPRESA_USUARIA_PADRAO_CNPJ:
            raise EmpresaUsuariaNaoEncontradaError(
                "A empresa usuária ainda não foi cadastrada"
            )
        return deepcopy(atual)

    def salvar_empresa_usuaria_atual(self, empresa: EmpresaUsuaria) -> EmpresaUsuaria:
        atual = self._empresa_atual()
        for outra in self._empresas_usuarias.values():
            if atual is not None and outra.id == atual.id:
                continue
            if outra.cnpj == empresa.cnpj:
                raise DuplicadoError(
                    f"O CNPJ {empresa.cnpj} já pertence a outra empresa usuária"
                )
            if outra.email.casefold() == empresa.email.casefold():
                raise DuplicadoError(
                    f"O e-mail {empresa.email} já pertence a outra empresa usuária"
                )

        if atual is None:
            empresa.id = self._proximo_id_empresa_usuaria
            self._proximo_id_empresa_usuaria += 1
        else:
            empresa.id = atual.id

        self._empresas_usuarias[empresa.id] = deepcopy(empresa)
        return empresa

    def salvar_produto(self, produto: Produto) -> Produto:
        if produto.empresa_usuaria_id not in self._empresas_usuarias:
            raise EmpresaUsuariaNaoEncontradaError(
                f"Empresa usuária {produto.empresa_usuaria_id} não existe"
            )
        if produto.id is not None:
            existente = self._produtos.get(produto.id)
            if existente is None or existente.empresa_usuaria_id != produto.empresa_usuaria_id:
                raise ProdutoNaoEncontradoError(
                    f"Produto {produto.id} não existe e não pode ser atualizado"
                )

        chave = validacao.chave_de_nome(produto.nome)
        for outro in self._produtos.values():
            if (outro.empresa_usuaria_id == produto.empresa_usuaria_id
                    and outro.id != produto.id
                    and validacao.chave_de_nome(outro.nome) == chave):
                raise DuplicadoError(
                    f"A empresa já tem um produto chamado {outro.nome!r}"
                )

        if produto.id is None:
            produto.id = self._proximo_id_produto
            self._proximo_id_produto += 1
        self._produtos[produto.id] = deepcopy(produto)
        return produto

    def buscar_produto(self, produto_id: int, empresa_usuaria_id: int) -> Produto:
        produto = self._produtos.get(produto_id)
        if produto is None or produto.empresa_usuaria_id != empresa_usuaria_id:
            raise ProdutoNaoEncontradoError(f"Produto {produto_id} não encontrado")
        return deepcopy(produto)

    def listar_produtos(self, empresa_usuaria_id: int) -> list[Produto]:
        return [
            deepcopy(p) for p in self._produtos.values()
            if p.empresa_usuaria_id == empresa_usuaria_id
        ]

    # --- Prospecções -------------------------------------------------------

    def salvar_prospeccao(self, prospeccao: Prospeccao) -> Prospeccao:
        if prospeccao.id is None:
            prospeccao.id = self._proximo_id_prospeccao
            self._proximo_id_prospeccao += 1

        self._prospeccoes[prospeccao.id] = deepcopy(prospeccao)
        return prospeccao

    def buscar_prospeccao(self, prospeccao_id: int) -> Prospeccao:
        if prospeccao_id not in self._prospeccoes:
            raise ProspeccaoNaoEncontradaError(
                f"Prospecção {prospeccao_id} não encontrada"
            )

        return deepcopy(self._prospeccoes[prospeccao_id])

    def listar_prospeccoes(
        self, perfil_id: Optional[int] = None
    ) -> list[Prospeccao]:
        return [
            deepcopy(p)
            for p in self._prospeccoes.values()
            if perfil_id is None or p.perfil_id == perfil_id
        ]

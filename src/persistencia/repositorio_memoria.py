"""Repositório em memória: serve para desenvolver e testar sem banco.

Os dados guardados são cópias. Alterar um objeto depois de salvá-lo, ou o
objeto devolvido por uma busca, não muda o que está guardado: só salvar de
novo muda. É o mesmo comportamento que o JSON e o PostgreSQL terão.
"""

from copy import deepcopy
from typing import Optional

from src.dominio.empresa import Empresa
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao
from src.excecoes import (
    EmpresaNaoEncontradaError,
    PerfilNaoEncontradoError,
    ProspeccaoNaoEncontradaError,
)
from src.persistencia.repositorio import Repositorio


class RepositorioMemoria(Repositorio):

    def __init__(self):
        self._perfis: dict[int, Perfil] = {}
        self._empresas: dict[str, Empresa] = {}
        self._prospeccoes: dict[int, Prospeccao] = {}
        self._proximo_id_perfil = 1
        self._proximo_id_prospeccao = 1

    # --- Perfis ------------------------------------------------------------

    def salvar_perfil(self, perfil: Perfil) -> Perfil:
        if perfil.id is None:
            perfil.id = self._proximo_id_perfil
            self._proximo_id_perfil += 1
        elif perfil.id not in self._perfis:
            raise PerfilNaoEncontradoError(
                f"Perfil {perfil.id} não existe e não pode ser atualizado"
            )

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

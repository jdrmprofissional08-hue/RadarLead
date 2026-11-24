"""Cadastro de perfis de cliente (BACK-02)."""

from typing import Optional

from src.dominio.perfil import Perfil
from src.persistencia.repositorio import Repositorio


class ServicoPerfil:

    def __init__(self, repositorio: Repositorio):
        self._repositorio = repositorio

    def cadastrar(
        self,
        nome: str,
        cnaes_desejados: list,
        porte_desejado: int,
        municipio_alvo_ibge: str,
        peso_segmento: float = 50,
        peso_porte: float = 25,
        peso_localizacao: float = 25,
        capital_minimo: float = 0,
        empresa_usuaria_id: Optional[int] = None,
        peso_cnae: Optional[float] = None,
        produto_id: Optional[int] = None,
    ) -> Perfil:
        """Valida os dados, cria o perfil e o salva.

        Os três pesos devem somar 100. peso_cnae é o nome antigo de
        peso_segmento e, se informado, vale no lugar dele.

        Levanta PerfilInvalidoError se algum campo for inválido (nada é salvo).
        """
        if peso_cnae is not None:
            peso_segmento = peso_cnae

        perfil = Perfil(
            nome=nome,
            cnaes_desejados=cnaes_desejados,
            porte_desejado=porte_desejado,
            municipio_alvo_ibge=municipio_alvo_ibge,
            peso_segmento=peso_segmento,
            peso_porte=peso_porte,
            peso_localizacao=peso_localizacao,
            capital_minimo=capital_minimo,
            empresa_usuaria_id=empresa_usuaria_id,
            produto_id=produto_id,
        )
        return self._repositorio.salvar_perfil(perfil)

    def buscar(self, perfil_id: int) -> Perfil:
        """Levanta PerfilNaoEncontradoError se o id não existir."""
        return self._repositorio.buscar_perfil(perfil_id)

    def listar(self) -> list[Perfil]:
        return self._repositorio.listar_perfis()

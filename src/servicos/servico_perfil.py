"""Cadastro de perfis de cliente (BACK-02)."""

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
        peso_cnae: float = 50,
        peso_porte: float = 25,
        peso_localizacao: float = 25,
    ) -> Perfil:
        """Valida os dados, cria o perfil e o salva.

        Levanta PerfilInvalidoError se algum campo for inválido (nada é salvo).
        """
        perfil = Perfil(
            nome=nome,
            cnaes_desejados=cnaes_desejados,
            porte_desejado=porte_desejado,
            municipio_alvo_ibge=municipio_alvo_ibge,
            peso_cnae=peso_cnae,
            peso_porte=peso_porte,
            peso_localizacao=peso_localizacao,
        )
        return self._repositorio.salvar_perfil(perfil)

    def buscar(self, perfil_id: int) -> Perfil:
        """Levanta PerfilNaoEncontradoError se o id não existir."""
        return self._repositorio.buscar_perfil(perfil_id)

    def listar(self) -> list[Perfil]:
        return self._repositorio.listar_perfis()

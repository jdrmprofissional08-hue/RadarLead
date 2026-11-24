"""Liga o serviço de prospecção ao pipeline de recomendação do José (src/Recomendadores).

O ServicoProspeccao chama recomendador.recomendar(empresas, perfil). Aqui esse
método monta, a CADA chamada, o pipeline completo com os dados do perfil:

    RecomendadorComFiltro(
        ClassificadorPorConteudo(pesos do perfil),
        FiltroElegibilidade(cnaes_desejados do perfil, raio),
        fornecedor,
    )

Por que a cada chamada: o classificador recebe os pesos no construtor e o
filtro recebe os CNAEs; ambos mudam de perfil para perfil. O pipeline também
guarda estado (eliminadas/aprovadas), então reutilizá-lo entre requisições
simultâneas misturaria resultados.

Regras do pipeline que afetam o resultado (vêm do código do José):
    - só passa empresa com situação cadastral 2 (ativa), CEP, latitude e
      longitude, e com CNAE (principal ou secundário) entre os desejados;
    - a distância até o fornecedor não pode passar de ``raio_km`` (máx. 350);
    - CNAEs "relacionados" ainda não existem no perfil, então vão vazios.

O import é feito só na primeira chamada: assim o resto do backend continua
funcionando (e testável) mesmo antes de a pasta src/Recomendadores entrar no
repositório.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from src.excecoes import RecomendadorError

# Goiânia (praça Cívica): usado enquanto o fornecedor real não for configurado.
LATITUDE_PADRAO = -16.6799
LONGITUDE_PADRAO = -49.2550
RAIO_KM_PADRAO = 350.0
RAIO_KM_MAXIMO = 350.0  # limite do pipeline do José


@dataclass(frozen=True)
class Fornecedor:
    """Quem prospecta: de onde a distância até cada empresa é medida."""

    latitude: float = LATITUDE_PADRAO
    longitude: float = LONGITUDE_PADRAO
    raio_km: float = RAIO_KM_PADRAO

    @classmethod
    def do_ambiente(cls, ambiente=None) -> "Fornecedor":
        """Lê RADARLEAD_FORNECEDOR_LAT, _LON e RADARLEAD_RAIO_KM (todas opcionais)."""
        ambiente = os.environ if ambiente is None else ambiente
        try:
            return cls(
                latitude=float(ambiente.get("RADARLEAD_FORNECEDOR_LAT", LATITUDE_PADRAO)),
                longitude=float(ambiente.get("RADARLEAD_FORNECEDOR_LON", LONGITUDE_PADRAO)),
                raio_km=float(ambiente.get("RADARLEAD_RAIO_KM", RAIO_KM_PADRAO)),
            )
        except ValueError as erro:
            raise RecomendadorError(
                "Configuração do fornecedor inválida (RADARLEAD_FORNECEDOR_LAT, "
                f"RADARLEAD_FORNECEDOR_LON e RADARLEAD_RAIO_KM devem ser números): {erro}"
            ) from erro


class RecomendadorDoProjeto:

    def __init__(self, fornecedor: Fornecedor = None):
        self._fornecedor = fornecedor or Fornecedor()

    @property
    def fornecedor(self) -> Fornecedor:
        return self._fornecedor

    def com_origem(self, latitude: float, longitude: float,
                   raio_km: float = None) -> "RecomendadorDoProjeto":
        """Cópia com outro ponto de origem (e raio), só para uma execução.

        Sem raio_km, vale o raio configurado no servidor.
        """
        return RecomendadorDoProjeto(Fornecedor(
            latitude=latitude,
            longitude=longitude,
            raio_km=self._fornecedor.raio_km if raio_km is None else raio_km,
        ))

    def recomendar(self, empresas: list, perfil: dict) -> list:
        try:
            from src.Recomendadores.classificador import ClassificadorPorConteudo
            from src.Recomendadores.filtro_elegibilidade import FiltroElegibilidade
            from src.Recomendadores.pipeline import RecomendadorComFiltro
        except ImportError as erro:
            raise RecomendadorError(
                "Não foi possível carregar o recomendador (pasta src/Recomendadores, "
                f"com R maiúsculo, do José): {erro}"
            ) from erro

        classificador = ClassificadorPorConteudo(
            peso_cnae=perfil["peso_segmento"],
            peso_porte=perfil["peso_porte"],
            peso_localizacao=perfil["peso_localizacao"],
        )
        filtro = FiltroElegibilidade(
            cnaes_diretos=perfil["cnaes_desejados"],
            cnaes_relacionados=[],
            raio_max_km=self._fornecedor.raio_km,
        )
        pipeline = RecomendadorComFiltro(
            classificador,
            filtro,
            {"latitude": self._fornecedor.latitude,
             "longitude": self._fornecedor.longitude},
        )
        return pipeline.recomendar(empresas, perfil)

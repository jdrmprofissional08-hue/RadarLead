"""Perfil: o que o usuário procura em um cliente."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.dominio import validacao
from src.excecoes import PerfilInvalidoError


@dataclass
class Perfil:
    nome: str
    cnaes_desejados: list[str]
    porte_desejado: int
    municipio_alvo_ibge: str
    peso_cnae: float = 50
    peso_porte: float = 25
    peso_localizacao: float = 25
    id: Optional[int] = None

    def __post_init__(self):
        try:
            self.nome = validacao.validar_texto(self.nome, "Nome do perfil")

            if not isinstance(self.cnaes_desejados, (list, tuple)) or not self.cnaes_desejados:
                raise ValueError("Informe ao menos um CNAE desejado")

            # remove duplicados mantendo a ordem
            self.cnaes_desejados = list(dict.fromkeys(
                validacao.normalizar_cnae(c) for c in self.cnaes_desejados
            ))

            self.porte_desejado = validacao.validar_inteiro(
                self.porte_desejado, "Porte desejado"
            )
            self.municipio_alvo_ibge = validacao.normalizar_ibge(
                self.municipio_alvo_ibge
            )
            self._validar_pesos()
        except ValueError as erro:
            raise PerfilInvalidoError(str(erro)) from erro

    def _validar_pesos(self):
        pesos = {
            "Peso do CNAE": self.peso_cnae,
            "Peso do porte": self.peso_porte,
            "Peso da localização": self.peso_localizacao,
        }

        for nome, valor in pesos.items():
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                raise ValueError(f"{nome} deve ser um número, recebido: {valor!r}")
            if valor < 0:
                raise ValueError(f"{nome} não pode ser negativo, recebido: {valor!r}")

        if sum(pesos.values()) <= 0:
            raise ValueError("A soma dos pesos deve ser maior que zero")

    def to_dict(self) -> dict:
        """Formato esperado pelos recomendadores (chaves do contrato do José)."""
        return {
            "id": self.id,
            "nome": self.nome,
            "cnaes_desejados": list(self.cnaes_desejados),
            "porte_desejado": self.porte_desejado,
            "municipio_alvo_ibge": self.municipio_alvo_ibge,
            "peso_cnae": self.peso_cnae,
            "peso_porte": self.peso_porte,
            "peso_localizacao": self.peso_localizacao,
        }

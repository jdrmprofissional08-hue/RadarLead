"""Empresa: dados já normalizados que os demais módulos consomem."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.dominio import validacao
from src.excecoes import EmpresaInvalidaError


@dataclass
class Empresa:
    cnpj: str
    razao_social: str
    cnae_principal: str
    porte: int
    municipio_ibge: str
    cnaes_secundarios: list[str] = field(default_factory=list)
    cep: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def __post_init__(self):
        try:
            self.cnpj = validacao.normalizar_cnpj(self.cnpj)
            self.razao_social = validacao.validar_texto(
                self.razao_social, "Razão social"
            )
            self.cnae_principal = validacao.normalizar_cnae(self.cnae_principal)
            self.porte = validacao.validar_inteiro(self.porte, "Porte")
            self.municipio_ibge = validacao.normalizar_ibge(self.municipio_ibge)
            self.cnaes_secundarios = [
                validacao.normalizar_cnae(c) for c in (self.cnaes_secundarios or [])
            ]
        except ValueError as erro:
            raise EmpresaInvalidaError(str(erro)) from erro

    def to_dict(self) -> dict:
        """Formato esperado pelos recomendadores (chaves do contrato do José)."""
        return {
            "cnpj": self.cnpj,
            "razao_social": self.razao_social,
            "cnae_principal": self.cnae_principal,
            "porte": self.porte,
            "municipio_ibge": self.municipio_ibge,
            "cnaes_secundarios": list(self.cnaes_secundarios),
            "cep": self.cep,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }

    @classmethod
    def from_dict(cls, dados: dict) -> "Empresa":
        obrigatorios = (
            "cnpj", "razao_social", "cnae_principal", "porte", "municipio_ibge"
        )

        if not isinstance(dados, dict):
            raise EmpresaInvalidaError("Os dados da empresa devem ser um dicionário")

        faltando = [chave for chave in obrigatorios if chave not in dados]
        if faltando:
            raise EmpresaInvalidaError(f"Campos obrigatórios ausentes: {faltando}")

        return cls(
            cnpj=dados["cnpj"],
            razao_social=dados["razao_social"],
            cnae_principal=dados["cnae_principal"],
            porte=dados["porte"],
            municipio_ibge=dados["municipio_ibge"],
            cnaes_secundarios=dados.get("cnaes_secundarios") or [],
            cep=dados.get("cep"),
            latitude=dados.get("latitude"),
            longitude=dados.get("longitude"),
        )

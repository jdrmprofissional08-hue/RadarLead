"""Empresa: dados já normalizados que os demais módulos consomem."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
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
    # Dados cadastrais. None significa "não informado": nenhum valor é inventado.
    # situacao_cadastral usa o código da Receita (2 = ativa). O recomendador só
    # aceita empresas ativas, então uma empresa sem situação é descartada por ele.
    situacao_cadastral: Optional[int] = None
    natureza_juridica: Optional[str] = None
    capital_social: Optional[float] = None
    data_inicio_atividade: Optional[date] = None
    data_situacao: Optional[date] = None

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

            if self.situacao_cadastral is not None:
                self.situacao_cadastral = validacao.normalizar_situacao(
                    self.situacao_cadastral
                )
            if self.natureza_juridica is not None:
                self.natureza_juridica = validacao.normalizar_natureza_juridica(
                    self.natureza_juridica
                )
            if self.capital_social is not None:
                self.capital_social = validacao.validar_capital(
                    self.capital_social, "Capital social"
                )
            if self.data_inicio_atividade is not None:
                self.data_inicio_atividade = validacao.validar_data(
                    self.data_inicio_atividade, "Data de início da atividade"
                )
            if self.data_situacao is not None:
                self.data_situacao = validacao.validar_data(
                    self.data_situacao, "Data da situação cadastral"
                )
        except ValueError as erro:
            raise EmpresaInvalidaError(str(erro)) from erro

    @property
    def ativa(self) -> bool:
        """True só quando a situação é conhecida e igual a 2 (ativa)."""
        return self.situacao_cadastral == 2

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
            "situacao_cadastral": self.situacao_cadastral,
            "natureza_juridica": self.natureza_juridica,
            "capital_social": self.capital_social,
            "data_inicio_atividade": (
                self.data_inicio_atividade.isoformat()
                if self.data_inicio_atividade else None
            ),
            "data_situacao": (
                self.data_situacao.isoformat() if self.data_situacao else None
            ),
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
            situacao_cadastral=dados.get("situacao_cadastral"),
            natureza_juridica=dados.get("natureza_juridica"),
            capital_social=dados.get("capital_social"),
            data_inicio_atividade=dados.get("data_inicio_atividade"),
            data_situacao=dados.get("data_situacao"),
        )

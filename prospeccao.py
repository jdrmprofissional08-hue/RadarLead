"""Prospecção: uma execução do sistema para um perfil, com os leads gerados."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from src.dominio import validacao
from src.dominio.lead import Lead
from src.excecoes import DadosInvalidosError


class StatusProspeccao(str, Enum):
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    ERRO = "erro"


@dataclass
class Prospeccao:
    perfil_id: int
    leads: list[Lead] = field(default_factory=list)
    total_empresas_avaliadas: int = 0
    criada_em: datetime = field(default_factory=datetime.now)
    status: StatusProspeccao = StatusProspeccao.CONCLUIDA
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "perfil_id": self.perfil_id,
            "total_empresas_avaliadas": self.total_empresas_avaliadas,
            "criada_em": self.criada_em.isoformat(),
            "status": StatusProspeccao(self.status).value,
            "leads": [lead.to_dict() for lead in self.leads],
        }

    @classmethod
    def from_dict(cls, dados: dict) -> "Prospeccao":
        """Recria uma Prospeccao a partir do formato de to_dict() (usado no JSON)."""
        if not isinstance(dados, dict):
            raise DadosInvalidosError("Os dados da prospecção devem ser um dicionário")

        faltando = [
            chave for chave in ("perfil_id", "criada_em", "leads")
            if chave not in dados
        ]
        if faltando:
            raise DadosInvalidosError(f"Campos obrigatórios ausentes: {faltando}")

        if not isinstance(dados["leads"], list):
            raise DadosInvalidosError("Os leads devem ser uma lista")

        try:
            perfil_id = validacao.validar_inteiro(dados["perfil_id"], "Id do perfil")
            total = validacao.validar_inteiro(
                dados.get("total_empresas_avaliadas", 0),
                "Total de empresas avaliadas",
            )
            if total < 0:
                raise ValueError("Total de empresas avaliadas não pode ser negativo")

            prospeccao_id = (
                None if dados.get("id") is None
                else validacao.validar_inteiro(dados["id"], "Id da prospecção")
            )

            if not isinstance(dados["criada_em"], str):
                raise ValueError("A data de criação deve ser um texto ISO 8601")
            criada_em = datetime.fromisoformat(dados["criada_em"])
            status = StatusProspeccao(
                dados.get("status", StatusProspeccao.CONCLUIDA.value)
            )
        except (ValueError, TypeError) as erro:
            raise DadosInvalidosError(str(erro)) from erro

        return cls(
            perfil_id=perfil_id,
            leads=[Lead.from_dict(item) for item in dados["leads"]],
            total_empresas_avaliadas=total,
            criada_em=criada_em,
            status=status,
            id=prospeccao_id,
        )

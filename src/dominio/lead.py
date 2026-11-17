"""Lead: uma empresa recomendada, com pontuação, justificativas e status."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from src.dominio import validacao
from src.excecoes import DadosInvalidosError


class StatusLead(str, Enum):
    NOVO = "novo"
    CONTATADO = "contatado"
    CONVERTIDO = "convertido"
    DESCARTADO = "descartado"


@dataclass
class Lead:
    cnpj: str
    razao_social: str
    pontuacao: float
    justificativas: list[str] = field(default_factory=list)
    status: StatusLead = StatusLead.NOVO

    @classmethod
    def de_recomendacao(cls, item: dict) -> "Lead":
        """Converte um item devolvido por Recomendador.recomendar() em Lead.

        Exige 'cnpj' e 'pontuacao'. 'razao_social' e 'justificativas' são
        opcionais. Levanta DadosInvalidosError se o item estiver fora do
        contrato.
        """
        if not isinstance(item, dict):
            raise DadosInvalidosError(
                f"Recomendação deve ser um dicionário, recebido: {item!r}"
            )

        for chave in ("cnpj", "pontuacao"):
            if chave not in item:
                raise DadosInvalidosError(
                    f"Recomendação sem o campo obrigatório '{chave}': {item!r}"
                )

        pontuacao = item["pontuacao"]
        if (
            isinstance(pontuacao, bool)
            or not isinstance(pontuacao, (int, float))
            or not math.isfinite(pontuacao)
        ):
            raise DadosInvalidosError(f"Pontuação inválida: {pontuacao!r}")

        justificativas = item.get("justificativas") or []
        if isinstance(justificativas, str):
            justificativas = [justificativas]
        if not isinstance(justificativas, (list, tuple)):
            raise DadosInvalidosError(
                f"Justificativas devem ser uma lista, recebido: {justificativas!r}"
            )

        try:
            cnpj = validacao.normalizar_cnpj(item["cnpj"])
        except ValueError as erro:
            raise DadosInvalidosError(str(erro)) from erro

        return cls(
            cnpj=cnpj,
            razao_social=item.get("razao_social") or "",
            pontuacao=pontuacao,
            justificativas=[str(j) for j in justificativas],
        )

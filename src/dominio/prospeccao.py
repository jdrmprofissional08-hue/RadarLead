"""Prospecção: uma execução do sistema para um perfil, com os leads gerados."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.dominio.lead import Lead


@dataclass
class Prospeccao:
    perfil_id: int
    leads: list[Lead] = field(default_factory=list)
    total_empresas_avaliadas: int = 0
    criada_em: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None

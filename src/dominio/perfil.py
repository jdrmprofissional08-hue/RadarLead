"""Perfil: o que o usuário procura em um cliente."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from src.dominio import validacao
from src.excecoes import PerfilInvalidoError


# códigos de porte da Receita Federal usados pelo esquema e pelo recomendador
PORTES_VALIDOS = (0, 1, 3, 5)


def _inteiro_se_redondo(valor):
    """50.0 -> 50; 33.33 continua 33.33."""
    return int(valor) if float(valor).is_integer() else valor


@dataclass
class Perfil:
    nome: str
    cnaes_desejados: list[str]
    porte_desejado: int
    municipio_alvo_ibge: str
    peso_segmento: float = 50
    peso_porte: float = 25
    peso_localizacao: float = 25
    capital_minimo: float = 0
    empresa_usuaria_id: Optional[int] = None
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
            if self.porte_desejado not in PORTES_VALIDOS:
                raise ValueError(
                    "Porte desejado deve ser 0 (não informado), 1 (microempresa), "
                    f"3 (pequeno porte) ou 5 (demais); recebido: {self.porte_desejado}"
                )
            self.municipio_alvo_ibge = validacao.normalizar_ibge(
                self.municipio_alvo_ibge
            )
            self._validar_pesos()
            self._validar_capital_minimo()
            # 50.0 vira 50: o recomendador exige pesos inteiros, e o banco
            # devolve NUMERIC como decimal.
            self.peso_segmento = _inteiro_se_redondo(self.peso_segmento)
            self.peso_porte = _inteiro_se_redondo(self.peso_porte)
            self.peso_localizacao = _inteiro_se_redondo(self.peso_localizacao)
            if self.empresa_usuaria_id is not None:
                self.empresa_usuaria_id = validacao.validar_inteiro(
                    self.empresa_usuaria_id, "Id da empresa usuária"
                )
        except ValueError as erro:
            raise PerfilInvalidoError(str(erro)) from erro

    @property
    def peso_cnae(self) -> float:
        """Nome antigo de peso_segmento (o recomendador ainda usa este nome)."""
        return self.peso_segmento

    def _validar_pesos(self):
        pesos = {
            "Peso do segmento": self.peso_segmento,
            "Peso do porte": self.peso_porte,
            "Peso da localização": self.peso_localizacao,
        }

        for nome, valor in pesos.items():
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                raise ValueError(f"{nome} deve ser um número, recebido: {valor!r}")
            if not math.isfinite(valor) or not 0 <= valor <= 100:
                raise ValueError(f"{nome} deve estar entre 0 e 100, recebido: {valor!r}")
            if round(valor, 2) != valor:
                raise ValueError(
                    f"{nome} aceita no máximo 2 casas decimais, recebido: {valor!r}"
                )

        # mesma regra do CHECK do banco (soma dos três pesos = 100)
        if not math.isclose(sum(pesos.values()), 100, abs_tol=1e-9):
            raise ValueError(
                f"A soma dos pesos deve ser 100, recebido: {sum(pesos.values())!r}"
            )

    def _validar_capital_minimo(self):
        valor = self.capital_minimo
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError(f"Capital mínimo deve ser um número, recebido: {valor!r}")
        if not math.isfinite(valor) or valor < 0:
            raise ValueError(f"Capital mínimo não pode ser negativo, recebido: {valor!r}")

    def to_dict(self) -> dict:
        """Formato esperado pelos recomendadores (chaves do contrato do José)."""
        return {
            "id": self.id,
            "nome": self.nome,
            "cnaes_desejados": list(self.cnaes_desejados),
            "porte_desejado": self.porte_desejado,
            "municipio_alvo_ibge": self.municipio_alvo_ibge,
            "peso_segmento": self.peso_segmento,
            "peso_cnae": self.peso_segmento,  # nome do contrato antigo
            "peso_porte": self.peso_porte,
            "peso_localizacao": self.peso_localizacao,
            "capital_minimo": self.capital_minimo,
            "empresa_usuaria_id": self.empresa_usuaria_id,
        }

    @classmethod
    def from_dict(cls, dados: dict) -> "Perfil":
        """Recria um Perfil a partir do formato de to_dict() (usado no JSON)."""
        obrigatorios = (
            "nome", "cnaes_desejados", "porte_desejado", "municipio_alvo_ibge"
        )

        if not isinstance(dados, dict):
            raise PerfilInvalidoError("Os dados do perfil devem ser um dicionário")

        faltando = [chave for chave in obrigatorios if chave not in dados]
        if faltando:
            raise PerfilInvalidoError(f"Campos obrigatórios ausentes: {faltando}")

        try:
            perfil_id = (
                None if dados.get("id") is None
                else validacao.validar_inteiro(dados["id"], "Id do perfil")
            )
        except ValueError as erro:
            raise PerfilInvalidoError(str(erro)) from erro

        return cls(
            nome=dados["nome"],
            cnaes_desejados=dados["cnaes_desejados"],
            porte_desejado=dados["porte_desejado"],
            municipio_alvo_ibge=dados["municipio_alvo_ibge"],
            # aceita o nome novo (peso_segmento) e o antigo (peso_cnae)
            peso_segmento=dados.get("peso_segmento", dados.get("peso_cnae", 50)),
            peso_porte=dados.get("peso_porte", 25),
            peso_localizacao=dados.get("peso_localizacao", 25),
            capital_minimo=dados.get("capital_minimo", 0),
            empresa_usuaria_id=dados.get("empresa_usuaria_id"),
            id=perfil_id,
        )

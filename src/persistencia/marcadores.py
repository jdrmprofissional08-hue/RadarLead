"""Marcadores de "não informado" para os bancos relacionais (PostgreSQL e MySQL).

O esquema de SBD exige (NOT NULL) situação cadastral, natureza jurídica, capital
social e datas em todo estabelecimento. A Empresa do domínio, porém, pode não ter
esses dados (None). Em vez de inventar valores que pareçam reais (como "ativa"),
o banco recebe um MARCADOR que nenhum dado verdadeiro assume:

    situação cadastral   '00'          (os códigos reais são 01, 02, 03, 04, 08)
    natureza jurídica    '0000'        (não existe)
    datas                1900-01-01    (nenhuma empresa é dessa época)
    capital social       0             (único marcador ambíguo: 0 também pode ser real)

Ao ler, o marcador volta a ser None. Assim, "desconhecido" nunca vira "ativa":
o recomendador só aceita situação 2 e descarta quem não a informa.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

SITUACAO_NAO_INFORMADA = "00"
NATUREZA_NAO_INFORMADA = "0000"
DATA_NAO_INFORMADA = date(1900, 1, 1)
CAPITAL_NAO_INFORMADO = 0
MOTIVO_PADRAO = "00"  # "SEM MOTIVO" é um código real da Receita

# Empresa usuária usada quando o repositório é criado sem informar
# empresa_usuaria_id. É um SUBSTITUTO PROVISÓRIO: o nome e o e-mail não são
# reais, e o CNPJ só tem os dígitos verificadores corretos (exigência do trigger
# do MySQL); não foi tirado de nenhuma empresa. Troque pelos dados da empresa
# usuária verdadeira quando houver cadastro.
EMPRESA_USUARIA_PADRAO_NOME = "Empresa usuária padrão"
EMPRESA_USUARIA_PADRAO_CNPJ = "12345678000195"
EMPRESA_USUARIA_PADRAO_EMAIL = "padrao@radarlead.invalid"


def situacao_para_codigo(situacao: Optional[int]) -> Optional[str]:
    """2 -> '02'. None devolve None (quem grava decide o marcador)."""
    return None if situacao is None else f"{situacao:02d}"


def codigo_para_situacao(codigo: Optional[str]) -> Optional[int]:
    """'02' -> 2; '00' (marcador) ou None -> None."""
    if codigo is None or codigo == SITUACAO_NAO_INFORMADA:
        return None
    return int(codigo)


def natureza_do_banco(codigo: Optional[str]) -> Optional[str]:
    return None if codigo in (None, NATUREZA_NAO_INFORMADA) else codigo


def data_do_banco(valor) -> Optional[date]:
    """Converte o valor lido do banco; o marcador 1900-01-01 vira None."""
    if valor is None:
        return None
    if hasattr(valor, "date") and callable(valor.date):  # datetime -> date
        valor = valor.date()
    return None if valor == DATA_NAO_INFORMADA else valor


def capital_do_banco(valor) -> Optional[float]:
    """NUMERIC/Decimal -> float. (0 continua 0: não dá para distinguir.)"""
    return None if valor is None else float(valor)

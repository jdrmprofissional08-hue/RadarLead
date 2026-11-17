"""Funções de validação e normalização usadas pelas classes de domínio.

Cada função devolve o valor padronizado ou levanta ValueError com uma
mensagem clara. As classes de domínio convertem esse ValueError na
exceção específica do projeto (ver src/excecoes.py).
"""

import re

_SEPARADORES = re.compile(r"[.\-/\s]")


def _para_digitos(valor, nome: str) -> str:
    """Converte int ou str (com pontuação) em uma string só de dígitos."""
    if isinstance(valor, bool) or not isinstance(valor, (int, str)):
        raise ValueError(f"{nome} deve ser texto ou inteiro, recebido: {valor!r}")

    texto = _SEPARADORES.sub("", str(valor))

    if not texto.isdigit():
        raise ValueError(f"{nome} deve conter apenas dígitos, recebido: {valor!r}")

    return texto


def normalizar_cnae(valor) -> str:
    """CNAE com 7 dígitos (aceita '62.04-0-00', '6204000' ou 6204000)."""
    texto = _para_digitos(valor, "CNAE")

    if len(texto) > 7:
        raise ValueError(f"CNAE deve ter no máximo 7 dígitos, recebido: {valor!r}")

    return texto.zfill(7)


def normalizar_cnpj(valor) -> str:
    """CNPJ com 14 dígitos (aceita '11.111.111/0001-11' ou só os dígitos)."""
    texto = _para_digitos(valor, "CNPJ")

    if isinstance(valor, int):
        texto = texto.zfill(14)

    if len(texto) != 14:
        raise ValueError(f"CNPJ deve ter 14 dígitos, recebido: {valor!r}")

    return texto


def normalizar_ibge(valor) -> str:
    """Código IBGE de município com 7 dígitos."""
    texto = _para_digitos(valor, "Código IBGE")

    if len(texto) != 7:
        raise ValueError(f"Código IBGE deve ter 7 dígitos, recebido: {valor!r}")

    return texto


def validar_inteiro(valor, nome: str) -> int:
    """Inteiro de verdade (bool e float não passam)."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"{nome} deve ser um número inteiro, recebido: {valor!r}")

    return valor


def validar_texto(valor, nome: str) -> str:
    """Texto não vazio, sem espaços nas pontas."""
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{nome} deve ser um texto não vazio, recebido: {valor!r}")

    return valor.strip()

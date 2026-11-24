"""Funções de validação e normalização usadas pelas classes de domínio.

Cada função devolve o valor padronizado ou levanta ValueError com uma
mensagem clara. As classes de domínio convertem esse ValueError na
exceção específica do projeto (ver src/excecoes.py).
"""

import math
import re
import unicodedata
from datetime import date, datetime

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


def cnpj_tem_digitos_validos(cnpj: str) -> bool:
    """Confere os dois dígitos verificadores (módulo 11) de um CNPJ de 14 dígitos.

    É a mesma regra do trigger do banco (sql/mysql/schema.sql). Sequências
    como 00000000000000 ou 11111111111111 são recusadas.
    """
    if len(cnpj) != 14 or not cnpj.isdigit() or len(set(cnpj)) == 1:
        return False

    def digito(base: str, pesos: list[int]) -> int:
        resto = sum(int(d) * p for d, p in zip(base, pesos)) % 11
        return 0 if resto < 2 else 11 - resto

    primeiro = digito(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    segundo = digito(cnpj[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return cnpj[12:] == f"{primeiro}{segundo}"


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_email(valor) -> str:
    """E-mail em formato simples (texto@dominio.ext), até 254 caracteres."""
    texto = validar_texto(valor, "E-mail")
    if len(texto) > 254 or not _EMAIL.match(texto):
        raise ValueError(f"E-mail em formato inválido: {valor!r}")
    return texto


def chave_de_nome(texto: str) -> str:
    """Forma de comparar nomes: sem espaços nas pontas, sem acentos, sem maiúsculas.

    É a mesma ideia da comparação do MySQL (que ignora acentos e maiúsculas),
    para que o repositório em memória e o banco concordem sobre "mesmo nome".
    """
    base = unicodedata.normalize("NFD", texto.strip())
    return "".join(c for c in base if not unicodedata.combining(c)).casefold()


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


# --- Dados cadastrais opcionais da empresa --------------------------------------

# Marcadores que o banco usa para "não informado" (ver persistencia/marcadores.py).
# Por isso nenhum valor real pode coincidir com eles.
_DATA_MARCADOR = date(1900, 1, 1)


def normalizar_situacao(valor) -> int:
    """Código da situação cadastral da Receita (1 nula, 2 ativa, 3 suspensa,
    4 inapta, 8 baixada). Aceita 2, '2' ou '02'."""
    if isinstance(valor, bool) or not isinstance(valor, (int, str)):
        raise ValueError(
            f"Situação cadastral deve ser um código numérico, recebido: {valor!r}"
        )

    texto = str(valor).strip()
    if not texto.isdigit() or len(texto) > 2 or int(texto) == 0:
        raise ValueError(
            f"Situação cadastral deve ser um código de 1 a 99, recebido: {valor!r}"
        )

    return int(texto)


def normalizar_natureza_juridica(valor) -> str:
    """Código da natureza jurídica com 4 dígitos (aceita 2062 ou '2062')."""
    texto = _para_digitos(valor, "Natureza jurídica")

    if len(texto) > 4 or int(texto) == 0:
        raise ValueError(
            f"Natureza jurídica deve ter até 4 dígitos e não ser zero, recebido: {valor!r}"
        )

    return texto.zfill(4)


def validar_capital(valor, nome: str = "Capital") -> float:
    """Número finito e não negativo (bool e texto não passam)."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"{nome} deve ser um número, recebido: {valor!r}")

    if not math.isfinite(valor) or valor < 0:
        raise ValueError(f"{nome} não pode ser negativo, recebido: {valor!r}")

    return valor


def validar_data(valor, nome: str) -> date:
    """date, datetime ou texto 'AAAA-MM-DD' (a hora, se houver, é descartada)."""
    if isinstance(valor, datetime):
        resultado = valor.date()
    elif isinstance(valor, date):
        resultado = valor
    elif isinstance(valor, str):
        try:
            resultado = date.fromisoformat(valor.strip()[:10])
        except ValueError:
            raise ValueError(
                f"{nome} deve estar no formato AAAA-MM-DD, recebido: {valor!r}"
            ) from None
    else:
        raise ValueError(f"{nome} deve ser uma data, recebido: {valor!r}")

    if resultado <= _DATA_MARCADOR:
        raise ValueError(f"{nome} inválida, recebido: {valor!r}")

    return resultado

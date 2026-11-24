"""Empresa usuária (quem usa o RadarLead) e os produtos/serviços que ela vende."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.dominio import validacao
from src.excecoes import EmpresaUsuariaInvalidaError, ProdutoInvalidoError


@dataclass
class EmpresaUsuaria:
    nome: str
    cnpj: str
    email: str
    id: Optional[int] = None

    def __post_init__(self):
        try:
            self.nome = validacao.validar_texto(self.nome, "Nome da empresa")
            self.cnpj = validacao.normalizar_cnpj(self.cnpj)
            if not validacao.cnpj_tem_digitos_validos(self.cnpj):
                raise ValueError(
                    f"CNPJ com dígitos verificadores inválidos: {self.cnpj}"
                )
            self.email = validacao.validar_email(self.email)
            if self.id is not None:
                self.id = validacao.validar_inteiro(self.id, "Id da empresa")
        except ValueError as erro:
            raise EmpresaUsuariaInvalidaError(str(erro)) from erro

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "cnpj": self.cnpj,
            "email": self.email,
        }

    @classmethod
    def from_dict(cls, dados: dict) -> "EmpresaUsuaria":
        if not isinstance(dados, dict):
            raise EmpresaUsuariaInvalidaError(
                "Os dados da empresa devem ser um dicionário"
            )
        faltando = [c for c in ("nome", "cnpj", "email") if c not in dados]
        if faltando:
            raise EmpresaUsuariaInvalidaError(
                f"Campos obrigatórios ausentes: {faltando}"
            )
        return cls(nome=dados["nome"], cnpj=dados["cnpj"], email=dados["email"],
                   id=dados.get("id"))


@dataclass
class Produto:
    nome: str
    descricao: Optional[str] = None
    empresa_usuaria_id: Optional[int] = None
    id: Optional[int] = None

    def __post_init__(self):
        try:
            self.nome = validacao.validar_texto(self.nome, "Nome do produto")
            if self.descricao is not None:
                if not isinstance(self.descricao, str):
                    raise ValueError(
                        f"Descrição deve ser um texto, recebido: {self.descricao!r}"
                    )
                self.descricao = self.descricao.strip() or None
            for campo, rotulo in (("empresa_usuaria_id", "Empresa do produto"),
                                  ("id", "Id do produto")):
                valor = getattr(self, campo)
                if valor is not None:
                    setattr(self, campo, validacao.validar_inteiro(valor, rotulo))
        except ValueError as erro:
            raise ProdutoInvalidoError(str(erro)) from erro

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "empresa_usuaria_id": self.empresa_usuaria_id,
            "nome": self.nome,
            "descricao": self.descricao,
        }

    @classmethod
    def from_dict(cls, dados: dict) -> "Produto":
        if not isinstance(dados, dict) or "nome" not in dados:
            raise ProdutoInvalidoError("Os dados do produto devem ter o campo 'nome'")
        return cls(
            nome=dados["nome"],
            descricao=dados.get("descricao"),
            empresa_usuaria_id=dados.get("empresa_usuaria_id"),
            id=dados.get("id"),
        )

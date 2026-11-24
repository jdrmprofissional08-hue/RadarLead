"""Repositório que guarda tudo em um único arquivo JSON (BACK-05).

Como funciona:
    - Ao criar o repositório, o arquivo é lido por inteiro. Se não existir
      (ou estiver vazio), o repositório começa vazio e o arquivo só é criado
      na primeira gravação.
    - Toda operação que salva dados grava o arquivo inteiro de novo.
    - A gravação é atômica: os dados vão para um arquivo temporário e só
      depois substituem o original. Se algo falhar no meio, o arquivo
      anterior continua intacto.
    - Se a gravação falhar, a memória volta ao estado de antes da operação.
      Ou a operação vale por completo (memória e arquivo), ou não vale.
    - Um arquivo ilegível ou corrompido nunca é sobrescrito: o construtor
      levanta PersistenciaError e o arquivo fica como está para você
      inspecionar.

Limitação: pensado para um único processo usando o arquivo por vez. Dois
programas abrindo o mesmo arquivo ao mesmo tempo podem sobrescrever os
dados um do outro.
"""

import json
import os
from copy import deepcopy
from pathlib import Path

from src.dominio.empresa import Empresa
from src.dominio.empresa_usuaria import EmpresaUsuaria, Produto
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao
from src.excecoes import DadosInvalidosError, PersistenciaError
from src.persistencia.repositorio_memoria import RepositorioMemoria


class RepositorioJson(RepositorioMemoria):

    VERSAO = 1

    def __init__(self, caminho):
        super().__init__()
        self._caminho = Path(caminho)
        self._carregar()

    # --- Operações de escrita: valem por completo ou não valem ---------------

    def salvar_perfil(self, perfil: Perfil) -> Perfil:
        id_antes = perfil.id
        base = super()
        try:
            return self._persistindo(lambda: base.salvar_perfil(perfil))
        except Exception:
            perfil.id = id_antes
            raise

    def salvar_empresa(self, empresa: Empresa) -> Empresa:
        base = super()
        return self._persistindo(lambda: base.salvar_empresa(empresa))

    def salvar_empresas(self, empresas: list[Empresa]) -> list[Empresa]:
        base = super()
        return self._persistindo(lambda: base.salvar_empresas(empresas))

    def salvar_empresa_usuaria_atual(self, empresa: EmpresaUsuaria) -> EmpresaUsuaria:
        id_antes = empresa.id
        base = super()
        try:
            return self._persistindo(lambda: base.salvar_empresa_usuaria_atual(empresa))
        except Exception:
            empresa.id = id_antes
            raise

    def salvar_produto(self, produto: Produto) -> Produto:
        id_antes = produto.id
        base = super()
        try:
            return self._persistindo(lambda: base.salvar_produto(produto))
        except Exception:
            produto.id = id_antes
            raise

    def salvar_prospeccao(self, prospeccao: Prospeccao) -> Prospeccao:
        id_antes = prospeccao.id
        base = super()
        try:
            return self._persistindo(lambda: base.salvar_prospeccao(prospeccao))
        except Exception:
            prospeccao.id = id_antes
            raise

    def _persistindo(self, operacao):
        """Executa a operação em memória e grava o arquivo; desfaz se falhar."""
        estado = self._copiar_estado()
        try:
            resultado = operacao()
            self._gravar()
            return resultado
        except Exception:
            self._restaurar_estado(estado)
            raise

    def _copiar_estado(self):
        return (
            deepcopy(self._perfis),
            deepcopy(self._empresas),
            deepcopy(self._prospeccoes),
            self._proximo_id_perfil,
            self._proximo_id_prospeccao,
            deepcopy(self._empresas_usuarias),
            deepcopy(self._produtos),
            self._proximo_id_empresa_usuaria,
            self._proximo_id_produto,
        )

    def _restaurar_estado(self, estado):
        (
            self._perfis,
            self._empresas,
            self._prospeccoes,
            self._proximo_id_perfil,
            self._proximo_id_prospeccao,
            self._empresas_usuarias,
            self._produtos,
            self._proximo_id_empresa_usuaria,
            self._proximo_id_produto,
        ) = estado

    # --- Gravação -------------------------------------------------------

    def _gravar(self):
        dados = {
            "versao": self.VERSAO,
            "proximo_id_perfil": self._proximo_id_perfil,
            "proximo_id_prospeccao": self._proximo_id_prospeccao,
            "perfis": [p.to_dict() for p in self._perfis.values()],
            "empresas": [e.to_dict() for e in self._empresas.values()],
            "prospeccoes": [p.to_dict() for p in self._prospeccoes.values()],
            "proximo_id_empresa_usuaria": self._proximo_id_empresa_usuaria,
            "proximo_id_produto": self._proximo_id_produto,
            "empresas_usuarias": [e.to_dict() for e in self._empresas_usuarias.values()],
            "produtos": [p.to_dict() for p in self._produtos.values()],
        }
        temporario = self._caminho.with_name(self._caminho.name + ".tmp")

        try:
            self._caminho.parent.mkdir(parents=True, exist_ok=True)

            with open(temporario, "w", encoding="utf-8") as arquivo:
                # allow_nan=False: NaN/Infinity não são JSON válido
                json.dump(dados, arquivo, ensure_ascii=False, indent=2,
                          allow_nan=False)
                arquivo.flush()
                os.fsync(arquivo.fileno())

            os.replace(temporario, self._caminho)
        except (OSError, TypeError, ValueError) as erro:
            try:
                temporario.unlink(missing_ok=True)
            except OSError:
                pass
            raise PersistenciaError(
                f"Não foi possível gravar {self._caminho}: {erro}"
            ) from erro

    # --- Leitura --------------------------------------------------------

    def _carregar(self):
        if not self._caminho.exists():
            return

        if self._caminho.is_dir():
            raise PersistenciaError(
                f"{self._caminho} é uma pasta, e não um arquivo JSON"
            )

        try:
            texto = self._caminho.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as erro:
            raise PersistenciaError(
                f"Não foi possível ler {self._caminho}: {erro}"
            ) from erro

        if not texto.strip():
            return  # arquivo vazio: começa sem dados

        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as erro:
            raise PersistenciaError(
                f"{self._caminho} não é um JSON válido "
                f"(linha {erro.lineno}, coluna {erro.colno}): {erro.msg}"
            ) from erro

        try:
            self._aplicar(dados)
        except (DadosInvalidosError, KeyError, TypeError, ValueError) as erro:
            raise PersistenciaError(
                f"Conteúdo inválido em {self._caminho}: {erro}"
            ) from erro

    def _aplicar(self, dados):
        if not isinstance(dados, dict):
            raise ValueError("a raiz do arquivo deve ser um objeto JSON")

        if dados.get("versao") != self.VERSAO:
            raise ValueError(
                f"versão do arquivo não suportada: {dados.get('versao')!r}"
            )

        for item in self._lista(dados, "perfis"):
            perfil = Perfil.from_dict(item)
            if perfil.id is None or perfil.id in self._perfis:
                raise ValueError(f"perfil com id ausente ou repetido: {perfil.id!r}")
            self._perfis[perfil.id] = perfil

        for item in self._lista(dados, "empresas"):
            empresa = Empresa.from_dict(item)
            if empresa.cnpj in self._empresas:
                raise ValueError(f"empresa com CNPJ repetido: {empresa.cnpj}")
            self._empresas[empresa.cnpj] = empresa

        for item in self._lista(dados, "prospeccoes"):
            prospeccao = Prospeccao.from_dict(item)
            if prospeccao.id is None or prospeccao.id in self._prospeccoes:
                raise ValueError(
                    f"prospecção com id ausente ou repetido: {prospeccao.id!r}"
                )
            self._prospeccoes[prospeccao.id] = prospeccao

        for item in self._lista(dados, "empresas_usuarias"):
            empresa_usuaria = EmpresaUsuaria.from_dict(item)
            if empresa_usuaria.id is None or empresa_usuaria.id in self._empresas_usuarias:
                raise ValueError(
                    f"empresa usuária com id ausente ou repetido: {empresa_usuaria.id!r}"
                )
            self._empresas_usuarias[empresa_usuaria.id] = empresa_usuaria

        for item in self._lista(dados, "produtos"):
            produto = Produto.from_dict(item)
            if produto.id is None or produto.id in self._produtos:
                raise ValueError(f"produto com id ausente ou repetido: {produto.id!r}")
            self._produtos[produto.id] = produto

        self._proximo_id_empresa_usuaria = self._proximo_id(
            dados.get("proximo_id_empresa_usuaria"), self._empresas_usuarias
        )
        self._proximo_id_produto = self._proximo_id(
            dados.get("proximo_id_produto"), self._produtos
        )
        self._proximo_id_perfil = self._proximo_id(
            dados.get("proximo_id_perfil"), self._perfis
        )
        self._proximo_id_prospeccao = self._proximo_id(
            dados.get("proximo_id_prospeccao"), self._prospeccoes
        )

    @staticmethod
    def _lista(dados: dict, chave: str) -> list:
        valor = dados.get(chave, [])
        if not isinstance(valor, list):
            raise ValueError(f"'{chave}' deve ser uma lista")
        return valor

    @staticmethod
    def _proximo_id(valor, registros: dict) -> int:
        """Próximo id livre: nunca menor que (maior id existente + 1)."""
        minimo = max(registros, default=0) + 1

        if valor is None:
            return minimo

        if isinstance(valor, bool) or not isinstance(valor, int):
            raise ValueError(f"contador de ids inválido: {valor!r}")

        return max(valor, minimo)

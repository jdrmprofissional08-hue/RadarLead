"""Repositório PostgreSQL (BACK-06): mesmo contrato do Repositorio.

Cada método público é uma transação: ou grava tudo, ou nada (rollback).
Os objetos recebidos só ganham id depois do commit.

Como o domínio da aplicação se encaixa no esquema (sql/schema.sql):

    Perfil        -> perfil_cliente_ideal + perfil_cnae
    Empresa       -> empresa + estabelecimento + cep (+ CNAEs secundários)
    Prospeccao    -> prospeccao + lead

Tabelas de código (município, CNAE, situação, motivo, natureza jurídica)
precisam estar carregadas antes: o repositório NÃO inventa descrições. Se um
código referenciado não existir, a gravação falha com PersistenciaError
dizendo qual. Veja sql/seed_dominios.sql para o mínimo.

DADOS CADASTRAIS (situação, natureza jurídica, capital social, datas): se a
Empresa os traz, são gravados; se vier None, o banco recebe um MARCADOR de
"não informado" (ver marcadores.py), nunca um valor que pareça real, e um dado
já existente no banco não é apagado por um None. Motivo da situação não faz
parte do domínio e recebe o código '00' (SEM MOTIVO) na primeira gravação.
Empresa usuária do perfil quando não informada -> a "Empresa usuária padrão" de
sql/seed_dominios.sql (criada na hora se não existir).

Diferenças em relação à memória/JSON, por limitação do esquema:
    - a ordem de cnaes_desejados e de cnaes_secundarios volta ordenada;
    - listar_empresas devolve em ordem de CNPJ;
    - os leads voltam por pontuação (maior primeiro), empates por CNPJ;
    - pontuação e pesos guardam 2 casas decimais;
    - razao_social do lead vem do cadastro da empresa;
    - uma justificativa não pode conter quebra de linha (é o separador);
    - toda Empresa precisa de CEP, pois o município é obtido pelo CEP.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import date
from typing import Optional

import psycopg2
from psycopg2 import errorcodes
from psycopg2.extras import execute_values

from src.dominio.empresa import Empresa
from src.dominio.lead import Lead, StatusLead
from src.dominio.perfil import Perfil
from src.dominio.prospeccao import Prospeccao, StatusProspeccao
from src.excecoes import (
    DadosInvalidosError,
    EmpresaNaoEncontradaError,
    PerfilInvalidoError,
    PerfilNaoEncontradoError,
    PersistenciaError,
    ProspeccaoNaoEncontradaError,
)
from src.persistencia.conexao import GerenciadorConexao
from src.persistencia.marcadores import (
    CAPITAL_NAO_INFORMADO,
    DATA_NAO_INFORMADA,
    EMPRESA_USUARIA_PADRAO_CNPJ,
    EMPRESA_USUARIA_PADRAO_EMAIL,
    EMPRESA_USUARIA_PADRAO_NOME,
    MOTIVO_PADRAO,
    NATUREZA_NAO_INFORMADA,
    SITUACAO_NAO_INFORMADA,
    capital_do_banco,
    codigo_para_situacao,
    data_do_banco,
    natureza_do_banco,
    situacao_para_codigo,
)
from src.persistencia.repositorio import Repositorio

SEPARADOR_JUSTIFICATIVAS = "\n"

_COLUNAS_PERFIL = (
    "id, empresa_usuaria_id, nome, porte_desejado, capital_minimo, "
    "municipio_alvo_ibge, peso_segmento, peso_porte, peso_localizacao"
)


class RepositorioPostgres(Repositorio):
    """
    gerenciador: GerenciadorConexao já configurado (cada operação abre e
        fecha a sua própria conexão).
    empresa_usuaria_id: dono dos perfis criados sem empresa_usuaria_id.
        Se None, usa a empresa usuária padrão.
    """

    def __init__(
        self,
        gerenciador: GerenciadorConexao,
        empresa_usuaria_id: Optional[int] = None,
    ):
        self._gerenciador = gerenciador
        self._empresa_usuaria_id = empresa_usuaria_id

    # --- Transação -------------------------------------------------------

    @contextmanager
    def _transacao(self):
        """Abre conexão, entrega um cursor e faz commit/rollback ao sair."""
        try:
            with self._gerenciador as ger:
                with ger.cursor() as cur:
                    yield cur
        except psycopg2.Error as erro:
            raise _traduzir_erro(erro) from erro

    # =====================================================================
    # Perfis
    # =====================================================================

    def salvar_perfil(self, perfil: Perfil) -> Perfil:
        with self._transacao() as cur:
            perfil_id, empresa_id = self._gravar_perfil(cur, perfil)

        perfil.id = perfil_id
        perfil.empresa_usuaria_id = empresa_id
        return perfil

    def buscar_perfil(self, perfil_id: int) -> Perfil:
        with self._transacao() as cur:
            cur.execute(
                f"SELECT {_COLUNAS_PERFIL} FROM perfil_cliente_ideal WHERE id = %s",
                (perfil_id,),
            )
            linhas = cur.fetchall()
            if not linhas:
                raise PerfilNaoEncontradoError(f"Perfil {perfil_id} não encontrado")
            return self._montar_perfis(cur, linhas)[0]

    def listar_perfis(self) -> list[Perfil]:
        with self._transacao() as cur:
            cur.execute(
                f"SELECT {_COLUNAS_PERFIL} FROM perfil_cliente_ideal ORDER BY id"
            )
            return self._montar_perfis(cur, cur.fetchall())

    def _gravar_perfil(self, cur, perfil: Perfil) -> tuple[int, int]:
        pesos = (perfil.peso_segmento, perfil.peso_porte, perfil.peso_localizacao)

        if perfil.id is None:
            empresa_id = (
                perfil.empresa_usuaria_id
                or self._empresa_usuaria_id
                or self._empresa_usuaria_padrao(cur)
            )
            cur.execute(
                """INSERT INTO perfil_cliente_ideal
                       (empresa_usuaria_id, nome, porte_desejado, capital_minimo,
                        municipio_alvo_ibge, peso_segmento, peso_porte,
                        peso_localizacao)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id, empresa_usuaria_id""",
                (empresa_id, perfil.nome, perfil.porte_desejado,
                 perfil.capital_minimo, perfil.municipio_alvo_ibge, *pesos),
            )
        else:
            # empresa_usuaria_id em branco mantém o dono atual do perfil
            cur.execute(
                """UPDATE perfil_cliente_ideal
                      SET empresa_usuaria_id = COALESCE(%s, empresa_usuaria_id),
                          nome = %s, porte_desejado = %s, capital_minimo = %s,
                          municipio_alvo_ibge = %s, peso_segmento = %s,
                          peso_porte = %s, peso_localizacao = %s
                    WHERE id = %s
                RETURNING id, empresa_usuaria_id""",
                (perfil.empresa_usuaria_id, perfil.nome, perfil.porte_desejado,
                 perfil.capital_minimo, perfil.municipio_alvo_ibge, *pesos,
                 perfil.id),
            )

        linha = cur.fetchone()
        if linha is None:
            raise PerfilNaoEncontradoError(
                f"Perfil {perfil.id} não existe e não pode ser atualizado"
            )
        perfil_id, empresa_id = linha

        cur.execute("DELETE FROM perfil_cnae WHERE perfil_id = %s", (perfil_id,))
        execute_values(
            cur,
            "INSERT INTO perfil_cnae (perfil_id, cnae) VALUES %s",
            [(perfil_id, cnae) for cnae in perfil.cnaes_desejados],
        )
        return perfil_id, empresa_id

    def _empresa_usuaria_padrao(self, cur) -> int:
        cur.execute(
            """INSERT INTO empresa_usuaria (nome, cnpj, email)
               VALUES (%s, %s, %s) ON CONFLICT (cnpj) DO NOTHING""",
            (EMPRESA_USUARIA_PADRAO_NOME, EMPRESA_USUARIA_PADRAO_CNPJ,
             EMPRESA_USUARIA_PADRAO_EMAIL),
        )
        cur.execute(
            "SELECT id FROM empresa_usuaria WHERE cnpj = %s",
            (EMPRESA_USUARIA_PADRAO_CNPJ,),
        )
        return cur.fetchone()[0]

    @staticmethod
    def _montar_perfis(cur, linhas) -> list[Perfil]:
        ids = [linha[0] for linha in linhas]
        cur.execute(
            """SELECT perfil_id, cnae FROM perfil_cnae
                WHERE perfil_id = ANY(%s) ORDER BY perfil_id, cnae""",
            (ids,),
        )
        cnaes: dict[int, list[str]] = {i: [] for i in ids}
        for perfil_id, cnae in cur.fetchall():
            cnaes[perfil_id].append(cnae)

        perfis = []
        for (id_, empresa_id, nome, porte, capital, ibge,
             p_seg, p_porte, p_loc) in linhas:
            try:
                perfis.append(Perfil(
                    id=id_,
                    empresa_usuaria_id=empresa_id,
                    nome=nome,
                    cnaes_desejados=cnaes[id_],
                    porte_desejado=porte,
                    municipio_alvo_ibge=ibge,
                    peso_segmento=float(p_seg),
                    peso_porte=float(p_porte),
                    peso_localizacao=float(p_loc),
                    capital_minimo=float(capital),
                ))
            except DadosInvalidosError as erro:
                raise PersistenciaError(
                    f"Perfil {id_} do banco não cabe no domínio: {erro}"
                ) from erro
        return perfis

    # =====================================================================
    # Empresas
    # =====================================================================

    def salvar_empresa(self, empresa: Empresa) -> Empresa:
        with self._transacao() as cur:
            self._gravar_empresa(cur, empresa)
        return empresa

    def salvar_empresas(self, empresas: list[Empresa]) -> list[Empresa]:
        # uma transação só: se uma falhar, nenhuma é gravada
        with self._transacao() as cur:
            for empresa in empresas:
                self._gravar_empresa(cur, empresa)
        return empresas

    def buscar_empresa(self, cnpj: str) -> Empresa:
        with self._transacao() as cur:
            empresas = self._ler_empresas(cur, "WHERE e.cnpj = %s", (cnpj,))
        if not empresas:
            raise EmpresaNaoEncontradaError(f"Empresa {cnpj} não encontrada")
        return empresas[0]

    def listar_empresas(self) -> list[Empresa]:
        with self._transacao() as cur:
            return self._ler_empresas(cur, "", ())

    def _gravar_empresa(self, cur, empresa: Empresa) -> None:
        cep = re.sub(r"\D", "", str(empresa.cep or ""))
        if len(cep) != 8:
            raise PersistenciaError(
                f"Empresa {empresa.cnpj}: o CEP é obrigatório (8 dígitos) para "
                f"gravar no PostgreSQL, pois o município é obtido pelo CEP; "
                f"recebido: {empresa.cep!r}"
            )

        cur.execute(
            """INSERT INTO cep (cep, latitude, longitude, municipio_ibge)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (cep) DO UPDATE SET
                   latitude = COALESCE(EXCLUDED.latitude, cep.latitude),
                   longitude = COALESCE(EXCLUDED.longitude, cep.longitude),
                   municipio_ibge = EXCLUDED.municipio_ibge""",
            (cep, empresa.latitude, empresa.longitude, empresa.municipio_ibge),
        )

        cnpj_basico = empresa.cnpj[:8]
        cur.execute(
            """INSERT INTO empresa
                   (cnpj_basico, razao_social, natureza_juridica_cod,
                    capital_social, porte_cod)
               VALUES (%s, %s, COALESCE(%s, %s), COALESCE(%s, %s), %s)
               ON CONFLICT (cnpj_basico) DO UPDATE SET
                   razao_social = EXCLUDED.razao_social,
                   porte_cod = EXCLUDED.porte_cod,
                   natureza_juridica_cod = COALESCE(%s, empresa.natureza_juridica_cod),
                   capital_social = COALESCE(%s, empresa.capital_social)""",
            (cnpj_basico, empresa.razao_social,
             empresa.natureza_juridica, NATUREZA_NAO_INFORMADA,
             empresa.capital_social, CAPITAL_NAO_INFORMADO, empresa.porte,
             empresa.natureza_juridica, empresa.capital_social),
        )

        cur.execute(
            """INSERT INTO estabelecimento
                   (cnpj, cnpj_basico, situacao_cod, data_situacao, motivo_cod,
                    data_inicio_atividade, cnae_principal, cep)
               VALUES (%s, %s, COALESCE(%s, %s), COALESCE(%s, %s), %s,
                       COALESCE(%s, %s), %s, %s)
               ON CONFLICT (cnpj) DO UPDATE SET
                   cnae_principal = EXCLUDED.cnae_principal,
                   cep = EXCLUDED.cep,
                   situacao_cod = COALESCE(%s, estabelecimento.situacao_cod),
                   data_situacao = COALESCE(%s, estabelecimento.data_situacao),
                   data_inicio_atividade =
                       COALESCE(%s, estabelecimento.data_inicio_atividade)""",
            (empresa.cnpj, cnpj_basico,
             situacao_para_codigo(empresa.situacao_cadastral), SITUACAO_NAO_INFORMADA,
             empresa.data_situacao, DATA_NAO_INFORMADA, MOTIVO_PADRAO,
             empresa.data_inicio_atividade, DATA_NAO_INFORMADA,
             empresa.cnae_principal, cep,
             situacao_para_codigo(empresa.situacao_cadastral),
             empresa.data_situacao, empresa.data_inicio_atividade),
        )

        cur.execute(
            "DELETE FROM estabelecimento_cnae_secundario WHERE cnpj = %s",
            (empresa.cnpj,),
        )
        execute_values(
            cur,
            "INSERT INTO estabelecimento_cnae_secundario (cnpj, cnae) VALUES %s",
            [(empresa.cnpj, cnae) for cnae in dict.fromkeys(empresa.cnaes_secundarios)],
        )

    @staticmethod
    def _ler_empresas(cur, filtro: str, parametros: tuple) -> list[Empresa]:
        cur.execute(
            f"""SELECT e.cnpj, emp.razao_social, e.cnae_principal, emp.porte_cod,
                       c.municipio_ibge, c.cep, c.latitude, c.longitude,
                       e.situacao_cod, emp.natureza_juridica_cod,
                       emp.capital_social, e.data_inicio_atividade, e.data_situacao
                  FROM estabelecimento e
                  JOIN empresa emp ON emp.cnpj_basico = e.cnpj_basico
                  LEFT JOIN cep c ON c.cep = e.cep
                  {filtro}
              ORDER BY e.cnpj""",
            parametros,
        )
        linhas = cur.fetchall()

        cur.execute(
            """SELECT cnpj, cnae FROM estabelecimento_cnae_secundario
                WHERE cnpj = ANY(%s) ORDER BY cnpj, cnae""",
            ([linha[0] for linha in linhas],),
        )
        secundarios: dict[str, list[str]] = {}
        for cnpj, cnae in cur.fetchall():
            secundarios.setdefault(cnpj, []).append(cnae)

        empresas = []
        for (cnpj, razao, cnae, porte, ibge, cep, lat, lon,
             situacao, natureza, capital, inicio, data_sit) in linhas:
            try:
                empresas.append(Empresa(
                    cnpj=cnpj,
                    razao_social=razao,
                    cnae_principal=cnae,
                    porte=porte,
                    municipio_ibge=ibge,
                    cnaes_secundarios=secundarios.get(cnpj, []),
                    cep=cep,
                    latitude=lat,
                    longitude=lon,
                    situacao_cadastral=codigo_para_situacao(situacao),
                    natureza_juridica=natureza_do_banco(natureza),
                    capital_social=capital_do_banco(capital),
                    data_inicio_atividade=data_do_banco(inicio),
                    data_situacao=data_do_banco(data_sit),
                ))
            except DadosInvalidosError as erro:
                raise PersistenciaError(
                    f"Estabelecimento {cnpj} do banco não cabe no domínio "
                    f"(CEP/município ausente?): {erro}"
                ) from erro
        return empresas

    # =====================================================================
    # Prospecções
    # =====================================================================

    def salvar_prospeccao(self, prospeccao: Prospeccao) -> Prospeccao:
        self._validar_leads(prospeccao)

        with self._transacao() as cur:
            prospeccao_id = self._gravar_prospeccao(cur, prospeccao)

        prospeccao.id = prospeccao_id
        return prospeccao

    def buscar_prospeccao(self, prospeccao_id: int) -> Prospeccao:
        with self._transacao() as cur:
            prospeccoes = self._ler_prospeccoes(cur, "WHERE id = %s", (prospeccao_id,))
        if not prospeccoes:
            raise ProspeccaoNaoEncontradaError(
                f"Prospecção {prospeccao_id} não encontrada"
            )
        return prospeccoes[0]

    def listar_prospeccoes(
        self, perfil_id: Optional[int] = None
    ) -> list[Prospeccao]:
        with self._transacao() as cur:
            if perfil_id is None:
                return self._ler_prospeccoes(cur, "", ())
            return self._ler_prospeccoes(cur, "WHERE perfil_id = %s", (perfil_id,))

    @staticmethod
    def _validar_leads(prospeccao: Prospeccao) -> None:
        cnpjs = [lead.cnpj for lead in prospeccao.leads]
        if len(set(cnpjs)) != len(cnpjs):
            raise DadosInvalidosError(
                "A prospecção tem leads repetidos para o mesmo CNPJ"
            )
        for lead in prospeccao.leads:
            if any(SEPARADOR_JUSTIFICATIVAS in j for j in lead.justificativas):
                raise DadosInvalidosError(
                    f"Justificativa do lead {lead.cnpj} contém quebra de linha, "
                    "que é usada como separador no banco"
                )

    @staticmethod
    def _gravar_prospeccao(cur, prospeccao: Prospeccao) -> int:
        status = StatusProspeccao(prospeccao.status).value
        valores = (
            prospeccao.perfil_id, prospeccao.criada_em, status,
            prospeccao.total_empresas_avaliadas,
        )

        if prospeccao.id is None:
            cur.execute(
                """INSERT INTO prospeccao
                       (perfil_id, executada_em, status, total_empresas_avaliadas)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                valores,
            )
        else:
            cur.execute(
                """INSERT INTO prospeccao
                       (id, perfil_id, executada_em, status, total_empresas_avaliadas)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET
                       perfil_id = EXCLUDED.perfil_id,
                       executada_em = EXCLUDED.executada_em,
                       status = EXCLUDED.status,
                       total_empresas_avaliadas = EXCLUDED.total_empresas_avaliadas
                   RETURNING id""",
                (prospeccao.id, *valores),
            )
            # com id explícito, a sequência precisa continuar depois dele
            cur.execute(
                """SELECT setval(pg_get_serial_sequence('prospeccao', 'id'),
                                 (SELECT max(id) FROM prospeccao))"""
            )

        prospeccao_id = cur.fetchone()[0] if prospeccao.id is None else prospeccao.id

        cur.execute("DELETE FROM lead WHERE prospeccao_id = %s", (prospeccao_id,))
        execute_values(
            cur,
            """INSERT INTO lead (prospeccao_id, cnpj, pontuacao, justificativa,
                                 status_contato) VALUES %s""",
            [
                (prospeccao_id, lead.cnpj, lead.pontuacao,
                 SEPARADOR_JUSTIFICATIVAS.join(lead.justificativas),
                 StatusLead(lead.status).value)
                for lead in prospeccao.leads
            ],
        )
        return prospeccao_id

    @staticmethod
    def _ler_prospeccoes(cur, filtro: str, parametros: tuple) -> list[Prospeccao]:
        cur.execute(
            f"""SELECT id, perfil_id, executada_em, status, total_empresas_avaliadas
                  FROM prospeccao {filtro} ORDER BY id""",
            parametros,
        )
        linhas = cur.fetchall()

        cur.execute(
            """SELECT l.prospeccao_id, l.cnpj, emp.razao_social, l.pontuacao,
                      l.justificativa, l.status_contato
                 FROM lead l
                 JOIN estabelecimento e ON e.cnpj = l.cnpj
                 JOIN empresa emp ON emp.cnpj_basico = e.cnpj_basico
                WHERE l.prospeccao_id = ANY(%s)
             ORDER BY l.prospeccao_id, l.pontuacao DESC, l.cnpj""",
            ([linha[0] for linha in linhas],),
        )
        leads: dict[int, list[Lead]] = {}
        for pid, cnpj, razao, pontuacao, justificativa, status in cur.fetchall():
            leads.setdefault(pid, []).append(Lead(
                cnpj=cnpj,
                razao_social=razao,
                pontuacao=float(pontuacao),
                justificativas=(
                    justificativa.split(SEPARADOR_JUSTIFICATIVAS)
                    if justificativa else []
                ),
                status=StatusLead(status),
            ))

        return [
            Prospeccao(
                id=id_,
                perfil_id=perfil_id,
                criada_em=executada_em,
                status=StatusProspeccao(status),
                total_empresas_avaliadas=total,
                leads=leads.get(id_, []),
            )
            for id_, perfil_id, executada_em, status, total in linhas
        ]


# --- Tradução de erros do psycopg2 ------------------------------------------

_DICA_DOMINIOS = (
    " (as tabelas de código, municípios e CNAEs precisam estar carregadas; "
    "veja sql/seed_dominios.sql)"
)


def _traduzir_erro(erro: psycopg2.Error) -> Exception:
    """Converte um erro do psycopg2 em uma exceção do projeto."""
    codigo = getattr(erro, "pgcode", None)
    diag = getattr(erro, "diag", None)
    restricao = getattr(diag, "constraint_name", None) or ""
    detalhe = (getattr(diag, "message_detail", None) or "").strip()

    if codigo == errorcodes.UNIQUE_VIOLATION:
        if restricao == "perfil_cliente_ideal_empresa_usuaria_id_nome_key":
            return PerfilInvalidoError(
                "Já existe um perfil com esse nome para a empresa usuária"
            )
        return PersistenciaError(
            f"Registro duplicado ({restricao}): {detalhe}".rstrip(": ")
        )

    if codigo == errorcodes.FOREIGN_KEY_VIOLATION:
        return PersistenciaError(
            f"Referência inexistente ({restricao}): {detalhe}{_DICA_DOMINIOS}"
        )

    if codigo == errorcodes.CHECK_VIOLATION:
        return PersistenciaError(f"Dado fora das regras do banco ({restricao})")

    if codigo == errorcodes.NOT_NULL_VIOLATION:
        coluna = getattr(diag, "column_name", None) or "?"
        return PersistenciaError(f"Campo obrigatório ausente no banco: {coluna}")

    resumo = str(erro).strip().splitlines()[0] if str(erro).strip() else ""
    return PersistenciaError(f"Falha no banco de dados: {resumo or type(erro).__name__}")

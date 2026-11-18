-- RadarLead: esquema relacional (PostgreSQL 16)
-- Baseado na Entrega 2 de Sistemas de Banco de Dados (Quadros 1 e 2).
--
-- Rode uma vez em um banco (ou schema) vazio:
--     psql -d radarlead -f sql/schema.sql
--     psql -d radarlead -f sql/seed_dominios.sql     (opcional, ver o arquivo)
--
-- Ordem de criação: tabelas de código -> município/CEP -> empresa/estabelecimento
-- -> domínio da aplicação (empresa usuária, produto, perfil, prospecção, lead).
--
-- Decisões que o documento deixa em aberto (marcadas com [DECISÃO]):
--   * logradouro/bairro do CEP e demais dados de contato ficam opcionais, para
--     não criar valores fictícios quando o dado não existe (seção 3.4, item k);
--   * estabelecimento.cep é opcional pelo mesmo motivo;
--   * prospeccao.total_empresas_avaliadas NÃO está no documento; foi acrescentada
--     porque o domínio da aplicação guarda esse número (é diferente da
--     contagem de leads, item f). Se o grupo preferir, basta remover a coluna.

-- =========================================================================
-- Dados públicos (Receita Federal / IBGE)
-- =========================================================================

CREATE TABLE natureza_juridica (
    codigo     VARCHAR(4)  PRIMARY KEY,
    descricao  TEXT        NOT NULL CHECK (btrim(descricao) <> '')
);

CREATE TABLE cnae (
    codigo     CHAR(7)     PRIMARY KEY CHECK (codigo ~ '^[0-9]{7}$'),
    descricao  TEXT        NOT NULL CHECK (btrim(descricao) <> '')
);

CREATE TABLE situacao_cadastral (
    codigo     VARCHAR(2)  PRIMARY KEY,
    descricao  TEXT        NOT NULL CHECK (btrim(descricao) <> '')
);

CREATE TABLE motivo_situacao (
    codigo     VARCHAR(2)  PRIMARY KEY,
    descricao  TEXT        NOT NULL CHECK (btrim(descricao) <> '')
);

-- Códigos como texto para preservar zeros à esquerda (item i).
CREATE TABLE municipio (
    codigo_ibge     CHAR(7)      PRIMARY KEY CHECK (codigo_ibge ~ '^[0-9]{7}$'),
    nome            TEXT         NOT NULL CHECK (btrim(nome) <> ''),
    uf              CHAR(2)      NOT NULL CHECK (uf ~ '^[A-Z]{2}$'),
    -- [DECISÃO] opcional: só é preenchido quando a correspondência Receita/IBGE existir.
    codigo_receita  VARCHAR(4)   UNIQUE CHECK (codigo_receita ~ '^[0-9]{4}$')
);

CREATE TABLE cep (
    cep             CHAR(8)           PRIMARY KEY CHECK (cep ~ '^[0-9]{8}$'),
    logradouro      TEXT,
    bairro          TEXT,
    latitude        DOUBLE PRECISION  CHECK (latitude  BETWEEN  -90 AND  90),
    longitude       DOUBLE PRECISION  CHECK (longitude BETWEEN -180 AND 180),
    municipio_ibge  CHAR(7)           NOT NULL REFERENCES municipio (codigo_ibge)
);
CREATE INDEX ix_cep_municipio ON cep (municipio_ibge);

CREATE TABLE empresa (
    cnpj_basico              CHAR(8)        PRIMARY KEY CHECK (cnpj_basico ~ '^[0-9]{8}$'),
    razao_social             TEXT           NOT NULL CHECK (btrim(razao_social) <> ''),
    natureza_juridica_cod    VARCHAR(4)     NOT NULL REFERENCES natureza_juridica (codigo),
    capital_social           NUMERIC(18, 2) NOT NULL CHECK (capital_social >= 0),
    porte_cod                SMALLINT       NOT NULL CHECK (porte_cod IN (0, 1, 3, 5)),
    qualificacao_responsavel VARCHAR(2),
    ente_federativo          TEXT,
    opcao_simples            BOOLEAN,
    data_opcao_simples       DATE,
    data_exclusao_simples    DATE,
    opcao_mei                BOOLEAN,
    data_opcao_mei           DATE,
    data_exclusao_mei        DATE
);

CREATE TABLE estabelecimento (
    cnpj                    CHAR(14)    PRIMARY KEY CHECK (cnpj ~ '^[0-9]{14}$'),
    cnpj_basico             CHAR(8)     NOT NULL REFERENCES empresa (cnpj_basico),
    nome_fantasia           TEXT,
    situacao_cod            VARCHAR(2)  NOT NULL REFERENCES situacao_cadastral (codigo),
    data_situacao           DATE        NOT NULL,
    motivo_cod              VARCHAR(2)  NOT NULL REFERENCES motivo_situacao (codigo),
    situacao_especial       TEXT,
    data_situacao_especial  DATE,
    data_inicio_atividade   DATE        NOT NULL,
    cnae_principal          CHAR(7)     NOT NULL REFERENCES cnae (codigo),
    tipo_logradouro         TEXT,
    logradouro              TEXT,
    numero                  TEXT,
    complemento             TEXT,
    bairro                  TEXT,
    -- [DECISÃO] opcional: sem CEP válido, o dado fica ausente (item k).
    cep                     CHAR(8)     REFERENCES cep (cep),
    ddd                     VARCHAR(4),
    telefone                VARCHAR(15),
    email                   TEXT,
    -- o CNPJ básico são os 8 primeiros dígitos do CNPJ
    CONSTRAINT ck_estab_cnpj_basico CHECK (cnpj_basico = left(cnpj, 8))
);
CREATE INDEX ix_estab_basico  ON estabelecimento (cnpj_basico);
CREATE INDEX ix_estab_cnae    ON estabelecimento (cnae_principal);
CREATE INDEX ix_estab_cep     ON estabelecimento (cep);

CREATE TABLE estabelecimento_cnae_secundario (
    cnpj  CHAR(14) NOT NULL REFERENCES estabelecimento (cnpj) ON DELETE CASCADE,
    cnae  CHAR(7)  NOT NULL REFERENCES cnae (codigo),
    PRIMARY KEY (cnpj, cnae)
);
CREATE INDEX ix_estab_cnae_sec_cnae ON estabelecimento_cnae_secundario (cnae);

-- =========================================================================
-- Domínio da aplicação
-- =========================================================================

CREATE TABLE empresa_usuaria (
    id     SERIAL  PRIMARY KEY,
    nome   TEXT    NOT NULL CHECK (btrim(nome) <> ''),
    cnpj   CHAR(14) NOT NULL UNIQUE CHECK (cnpj ~ '^[0-9]{14}$'),
    email  TEXT    NOT NULL UNIQUE CHECK (btrim(email) <> '')
);

CREATE TABLE produto (
    id                  SERIAL  PRIMARY KEY,
    empresa_usuaria_id  INTEGER NOT NULL REFERENCES empresa_usuaria (id),
    nome                TEXT    NOT NULL CHECK (btrim(nome) <> ''),
    descricao           TEXT,
    UNIQUE (empresa_usuaria_id, nome),
    -- necessário para a FK composta de perfil_cliente_ideal
    UNIQUE (id, empresa_usuaria_id)
);

CREATE TABLE perfil_cliente_ideal (
    id                   SERIAL        PRIMARY KEY,
    empresa_usuaria_id   INTEGER       NOT NULL REFERENCES empresa_usuaria (id),
    produto_id           INTEGER,
    nome                 TEXT          NOT NULL CHECK (btrim(nome) <> ''),
    porte_desejado       SMALLINT      NOT NULL CHECK (porte_desejado IN (0, 1, 3, 5)),
    capital_minimo       NUMERIC(18, 2) NOT NULL DEFAULT 0 CHECK (capital_minimo >= 0),
    municipio_alvo_ibge  CHAR(7)       REFERENCES municipio (codigo_ibge),
    peso_segmento        NUMERIC(5, 2) NOT NULL CHECK (peso_segmento   BETWEEN 0 AND 100),
    peso_porte           NUMERIC(5, 2) NOT NULL CHECK (peso_porte      BETWEEN 0 AND 100),
    peso_localizacao     NUMERIC(5, 2) NOT NULL CHECK (peso_localizacao BETWEEN 0 AND 100),
    CONSTRAINT ck_perfil_pesos_somam_100
        CHECK (peso_segmento + peso_porte + peso_localizacao = 100),
    UNIQUE (empresa_usuaria_id, nome),
    -- Garante que o produto pertence à mesma empresa usuária do perfil.
    -- Com produto_id nulo (perfil geral) a FK não é verificada (MATCH SIMPLE).
    FOREIGN KEY (produto_id, empresa_usuaria_id)
        REFERENCES produto (id, empresa_usuaria_id)
);

CREATE TABLE perfil_cnae (
    perfil_id  INTEGER NOT NULL REFERENCES perfil_cliente_ideal (id) ON DELETE CASCADE,
    cnae       CHAR(7) NOT NULL REFERENCES cnae (codigo),
    PRIMARY KEY (perfil_id, cnae)
);

CREATE TABLE prospeccao (
    id                        SERIAL     PRIMARY KEY,
    perfil_id                 INTEGER    NOT NULL REFERENCES perfil_cliente_ideal (id),
    executada_em              TIMESTAMP  NOT NULL,
    status                    VARCHAR(12) NOT NULL
        CHECK (status IN ('em_andamento', 'concluida', 'erro')),
    -- [DECISÃO] não consta no documento; ver o cabeçalho deste arquivo.
    total_empresas_avaliadas  INTEGER    NOT NULL DEFAULT 0
        CHECK (total_empresas_avaliadas >= 0)
);
CREATE INDEX ix_prospeccao_perfil ON prospeccao (perfil_id);

CREATE TABLE lead (
    prospeccao_id   INTEGER       NOT NULL REFERENCES prospeccao (id) ON DELETE CASCADE,
    cnpj            CHAR(14)      NOT NULL REFERENCES estabelecimento (cnpj),
    -- pontuação histórica, gravada no momento da execução (item e)
    pontuacao       NUMERIC(5, 2) NOT NULL CHECK (pontuacao BETWEEN 0 AND 100),
    -- texto único; várias justificativas são separadas por quebra de linha
    justificativa   TEXT          NOT NULL DEFAULT '',
    status_contato  VARCHAR(12)   NOT NULL DEFAULT 'novo'
        CHECK (status_contato IN ('novo', 'contatado', 'convertido', 'descartado')),
    PRIMARY KEY (prospeccao_id, cnpj)
);
CREATE INDEX ix_lead_cnpj ON lead (cnpj);

-- Total de leads não é armazenado: é derivado por contagem (item f).
CREATE VIEW vw_prospeccao_resumo AS
SELECT p.id            AS prospeccao_id,
       p.perfil_id,
       p.executada_em,
       p.status,
       p.total_empresas_avaliadas,
       count(l.cnpj)   AS total_leads
FROM prospeccao p
LEFT JOIN lead l ON l.prospeccao_id = p.id
GROUP BY p.id;

-- RadarLead: banco completo para importar (gerado de schema.sql + seed_dominios.sql + seed_demo.sql).
-- mysql -u root -p < sql/mysql/radarlead_completo.sql
-- Recria o banco 'radarlead' do zero: APAGA o que existir com esse nome.
DROP DATABASE IF EXISTS radarlead;
CREATE DATABASE radarlead CHARACTER SET utf8mb4;
USE radarlead;

-- RadarLead: esquema relacional (MySQL 8.0.19 ou superior)
-- Baseado na Entrega 2 de Sistemas de Banco de Dados (Quadros 1 e 2).
--
-- Como rodar (MySQL Workbench):
--     1. crie o banco:   CREATE DATABASE radarlead CHARACTER SET utf8mb4;
--     2. dê duplo clique no schema "radarlead" para torná-lo o padrão;
--     3. File > Run SQL Script... > sql/mysql/schema.sql
--     4. (opcional) o mesmo para sql/mysql/seed_dominios.sql
--
-- Pela linha de comando:
--     mysql -u root -p radarlead < sql/mysql/schema.sql
--     mysql -u root -p radarlead < sql/mysql/seed_dominios.sql
--
-- Ordem de criação: tabelas de código -> município/CEP -> empresa/estabelecimento
-- -> domínio da aplicação (empresa usuária, produto, perfil, prospecção, lead)
-- -> função e triggers de validação do CNPJ -> view.
--
-- Códigos (CNPJ, CEP, CNAE...) usam ascii_bin: ocupam menos espaço, preservam
-- zeros à esquerda e a comparação é exata, o que o CHECK por expressão regular
-- exige (por exemplo, a UF só com letras maiúsculas).
--
-- Diferenças em relação à versão PostgreSQL (sql/schema.sql), por limitação do
-- MySQL: SERIAL vira AUTO_INCREMENT; TIMESTAMP vira DATETIME(6); TEXT em colunas
-- com UNIQUE vira VARCHAR; nomes e e-mails únicos ignoram maiúsculas e acentos
-- (collation padrão do MySQL); os nomes das restrições CHECK são únicos no banco
-- inteiro, e não só na tabela.
--
-- Decisões que o documento deixa em aberto (marcadas com [DECISÃO]):
--   * logradouro/bairro do CEP e demais dados de contato ficam opcionais, para
--     não criar valores fictícios quando o dado não existe;
--   * municipio.codigo_receita e estabelecimento.cep são opcionais pelo mesmo
--     motivo;
--   * prospeccao.total_empresas_avaliadas NÃO está no documento; foi acrescentada
--     porque o domínio da aplicação guarda esse número (é diferente da
--     contagem de leads). Se o grupo preferir, basta remover a coluna;
--   * perfil_cliente_ideal.produto_id e a tabela produto também vêm do modelo
--     do grupo, e não do Quadro 1.

-- =========================================================================
-- Dados públicos (Receita Federal / IBGE)
-- =========================================================================

CREATE TABLE natureza_juridica (
    codigo     VARCHAR(4) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    descricao  TEXT       NOT NULL,
    PRIMARY KEY (codigo),
    CHECK (TRIM(descricao) <> '')
);

CREATE TABLE cnae (
    codigo     CHAR(7) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    descricao  TEXT    NOT NULL,
    PRIMARY KEY (codigo),
    CHECK (codigo REGEXP '^[0-9]{7}$'),
    CHECK (TRIM(descricao) <> '')
);

CREATE TABLE situacao_cadastral (
    codigo     VARCHAR(2) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    descricao  TEXT       NOT NULL,
    PRIMARY KEY (codigo),
    CHECK (TRIM(descricao) <> '')
);

CREATE TABLE motivo_situacao (
    codigo     VARCHAR(2) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    descricao  TEXT       NOT NULL,
    PRIMARY KEY (codigo),
    CHECK (TRIM(descricao) <> '')
);

CREATE TABLE municipio (
    codigo_ibge     CHAR(7) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    nome            VARCHAR(120) NOT NULL,
    uf              CHAR(2) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    -- [DECISÃO] opcional: só é preenchido quando a correspondência Receita/IBGE existir.
    codigo_receita  CHAR(4) CHARACTER SET ascii COLLATE ascii_bin NULL,
    PRIMARY KEY (codigo_ibge),
    UNIQUE (codigo_receita),
    CHECK (codigo_ibge REGEXP '^[0-9]{7}$'),
    CHECK (TRIM(nome) <> ''),
    CHECK (uf REGEXP '^[A-Z]{2}$'),
    CHECK (codigo_receita REGEXP '^[0-9]{4}$')
);

CREATE TABLE cep (
    cep             CHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    logradouro      TEXT,
    bairro          TEXT,
    latitude        DOUBLE,
    longitude       DOUBLE,
    municipio_ibge  CHAR(7) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    PRIMARY KEY (cep),
    CONSTRAINT fk_cep_municipio FOREIGN KEY (municipio_ibge)
        REFERENCES municipio (codigo_ibge),
    CHECK (cep REGEXP '^[0-9]{8}$'),
    CHECK (latitude  BETWEEN  -90 AND  90),
    CHECK (longitude BETWEEN -180 AND 180)
);
CREATE INDEX ix_cep_municipio ON cep (municipio_ibge);

CREATE TABLE empresa (
    cnpj_basico              CHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    razao_social             TEXT           NOT NULL,
    natureza_juridica_cod    VARCHAR(4) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    capital_social           DECIMAL(18, 2) NOT NULL,
    porte_cod                SMALLINT       NOT NULL,
    qualificacao_responsavel VARCHAR(2),
    ente_federativo          TEXT,
    opcao_simples            BOOLEAN,
    data_opcao_simples       DATE,
    data_exclusao_simples    DATE,
    opcao_mei                BOOLEAN,
    data_opcao_mei           DATE,
    data_exclusao_mei        DATE,
    PRIMARY KEY (cnpj_basico),
    CONSTRAINT fk_empresa_natureza FOREIGN KEY (natureza_juridica_cod)
        REFERENCES natureza_juridica (codigo),
    CHECK (cnpj_basico REGEXP '^[0-9]{8}$'),
    CHECK (TRIM(razao_social) <> ''),
    CHECK (capital_social >= 0),
    CHECK (porte_cod IN (0, 1, 3, 5))
);

CREATE TABLE estabelecimento (
    cnpj                    CHAR(14) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    cnpj_basico             CHAR(8)  CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    nome_fantasia           TEXT,
    situacao_cod            VARCHAR(2) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    data_situacao           DATE       NOT NULL,
    motivo_cod              VARCHAR(2) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    situacao_especial       TEXT,
    data_situacao_especial  DATE,
    data_inicio_atividade   DATE       NOT NULL,
    cnae_principal          CHAR(7)    CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    tipo_logradouro         TEXT,
    logradouro              TEXT,
    numero                  TEXT,
    complemento             TEXT,
    bairro                  TEXT,
    -- [DECISÃO] opcional: sem CEP válido, o dado fica ausente.
    cep                     CHAR(8)    CHARACTER SET ascii COLLATE ascii_bin NULL,
    ddd                     VARCHAR(4),
    telefone                VARCHAR(15),
    email                   TEXT,
    PRIMARY KEY (cnpj),
    CONSTRAINT fk_estab_empresa   FOREIGN KEY (cnpj_basico)    REFERENCES empresa (cnpj_basico),
    CONSTRAINT fk_estab_situacao  FOREIGN KEY (situacao_cod)   REFERENCES situacao_cadastral (codigo),
    CONSTRAINT fk_estab_motivo    FOREIGN KEY (motivo_cod)     REFERENCES motivo_situacao (codigo),
    CONSTRAINT fk_estab_cnae      FOREIGN KEY (cnae_principal) REFERENCES cnae (codigo),
    CONSTRAINT fk_estab_cep       FOREIGN KEY (cep)            REFERENCES cep (cep),
    CHECK (cnpj REGEXP '^[0-9]{14}$'),
    -- o CNPJ básico são os 8 primeiros dígitos do CNPJ
    CONSTRAINT ck_estab_cnpj_basico CHECK (cnpj_basico = LEFT(cnpj, 8))
);
CREATE INDEX ix_estab_basico ON estabelecimento (cnpj_basico);
CREATE INDEX ix_estab_cnae   ON estabelecimento (cnae_principal);

CREATE TABLE estabelecimento_cnae_secundario (
    cnpj  CHAR(14) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    cnae  CHAR(7)  CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    PRIMARY KEY (cnpj, cnae),
    CONSTRAINT fk_cnae_sec_estab FOREIGN KEY (cnpj) REFERENCES estabelecimento (cnpj)
        ON DELETE CASCADE,
    CONSTRAINT fk_cnae_sec_cnae  FOREIGN KEY (cnae) REFERENCES cnae (codigo)
);
CREATE INDEX ix_estab_cnae_sec_cnae ON estabelecimento_cnae_secundario (cnae);

-- =========================================================================
-- Domínio da aplicação
-- ("lead" é palavra reservada no MySQL 8: sempre entre crases.)
-- =========================================================================

CREATE TABLE empresa_usuaria (
    id     INT          NOT NULL AUTO_INCREMENT,
    nome   VARCHAR(200) NOT NULL,
    cnpj   CHAR(14) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    email  VARCHAR(254) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (cnpj),
    UNIQUE (email),
    CHECK (TRIM(nome) <> ''),
    CHECK (cnpj REGEXP '^[0-9]{14}$'),
    CHECK (TRIM(email) <> '')
);

CREATE TABLE produto (
    id                  INT          NOT NULL AUTO_INCREMENT,
    empresa_usuaria_id  INT          NOT NULL,
    nome                VARCHAR(200) NOT NULL,
    descricao           TEXT,
    PRIMARY KEY (id),
    CONSTRAINT uq_produto_empresa_nome UNIQUE (empresa_usuaria_id, nome),
    -- necessário para a FK composta de perfil_cliente_ideal
    CONSTRAINT uq_produto_id_empresa UNIQUE (id, empresa_usuaria_id),
    CONSTRAINT fk_produto_empresa_usuaria FOREIGN KEY (empresa_usuaria_id)
        REFERENCES empresa_usuaria (id),
    CHECK (TRIM(nome) <> '')
);

CREATE TABLE perfil_cliente_ideal (
    id                   INT           NOT NULL AUTO_INCREMENT,
    empresa_usuaria_id   INT           NOT NULL,
    produto_id           INT           NULL,
    nome                 VARCHAR(200)  NOT NULL,
    porte_desejado       SMALLINT      NOT NULL,
    capital_minimo       DECIMAL(18, 2) NOT NULL DEFAULT 0,
    municipio_alvo_ibge  CHAR(7) CHARACTER SET ascii COLLATE ascii_bin NULL,
    peso_segmento        DECIMAL(5, 2) NOT NULL,
    peso_porte           DECIMAL(5, 2) NOT NULL,
    peso_localizacao     DECIMAL(5, 2) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_perfil_empresa_nome UNIQUE (empresa_usuaria_id, nome),
    CONSTRAINT fk_perfil_empresa_usuaria FOREIGN KEY (empresa_usuaria_id)
        REFERENCES empresa_usuaria (id),
    CONSTRAINT fk_perfil_municipio FOREIGN KEY (municipio_alvo_ibge)
        REFERENCES municipio (codigo_ibge),
    -- Garante que o produto pertence à mesma empresa usuária do perfil.
    -- Com produto_id nulo (perfil geral) a FK não é verificada.
    CONSTRAINT fk_perfil_produto FOREIGN KEY (produto_id, empresa_usuaria_id)
        REFERENCES produto (id, empresa_usuaria_id),
    CHECK (TRIM(nome) <> ''),
    CHECK (porte_desejado IN (0, 1, 3, 5)),
    CHECK (capital_minimo >= 0),
    CHECK (peso_segmento    BETWEEN 0 AND 100),
    CHECK (peso_porte       BETWEEN 0 AND 100),
    CHECK (peso_localizacao BETWEEN 0 AND 100),
    CONSTRAINT ck_perfil_pesos_somam_100
        CHECK (peso_segmento + peso_porte + peso_localizacao = 100)
);

CREATE TABLE perfil_cnae (
    perfil_id  INT     NOT NULL,
    cnae       CHAR(7) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    PRIMARY KEY (perfil_id, cnae),
    CONSTRAINT fk_perfil_cnae_perfil FOREIGN KEY (perfil_id)
        REFERENCES perfil_cliente_ideal (id) ON DELETE CASCADE,
    CONSTRAINT fk_perfil_cnae_cnae FOREIGN KEY (cnae) REFERENCES cnae (codigo)
);

CREATE TABLE prospeccao (
    id                        INT         NOT NULL AUTO_INCREMENT,
    perfil_id                 INT         NOT NULL,
    executada_em              DATETIME(6) NOT NULL,
    status                    VARCHAR(12) NOT NULL,
    -- [DECISÃO] não consta no documento; ver o cabeçalho deste arquivo.
    total_empresas_avaliadas  INT         NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    CONSTRAINT fk_prospeccao_perfil FOREIGN KEY (perfil_id)
        REFERENCES perfil_cliente_ideal (id),
    CHECK (status IN ('em_andamento', 'concluida', 'erro')),
    CHECK (total_empresas_avaliadas >= 0)
);
CREATE INDEX ix_prospeccao_perfil ON prospeccao (perfil_id);

CREATE TABLE `lead` (
    prospeccao_id   INT           NOT NULL,
    cnpj            CHAR(14) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    -- pontuação histórica, gravada no momento da execução
    pontuacao       DECIMAL(5, 2) NOT NULL,
    -- texto único; várias justificativas são separadas por quebra de linha
    justificativa   TEXT          NOT NULL,
    status_contato  VARCHAR(12)   NOT NULL DEFAULT 'novo',
    PRIMARY KEY (prospeccao_id, cnpj),
    CONSTRAINT fk_lead_prospeccao FOREIGN KEY (prospeccao_id)
        REFERENCES prospeccao (id) ON DELETE CASCADE,
    CONSTRAINT fk_lead_estabelecimento FOREIGN KEY (cnpj)
        REFERENCES estabelecimento (cnpj),
    CHECK (pontuacao BETWEEN 0 AND 100),
    CHECK (status_contato IN ('novo', 'contatado', 'convertido', 'descartado'))
);
CREATE INDEX ix_lead_cnpj ON `lead` (cnpj);

-- =========================================================================
-- Validação do CNPJ da empresa usuária (dígitos verificadores)
-- =========================================================================
-- O CHECK por expressão regular só confere o formato (14 dígitos). Os dois
-- últimos dígitos são calculados a partir dos anteriores (módulo 11); a função
-- abaixo refaz a conta e os triggers recusam o CNPJ que não bater. Vale só para
-- a empresa usuária: o CNPJ dos estabelecimentos vem da Receita Federal.

DELIMITER $$

CREATE FUNCTION fn_cnpj_valido(p_cnpj CHAR(14))
RETURNS TINYINT(1)
DETERMINISTIC
NO SQL
BEGIN
    DECLARE i     INT DEFAULT 1;
    DECLARE soma  INT DEFAULT 0;
    DECLARE resto INT;
    DECLARE dv1   INT;
    DECLARE dv2   INT;

    IF p_cnpj IS NULL OR p_cnpj NOT REGEXP '^[0-9]{14}$' THEN
        RETURN 0;
    END IF;

    -- 00000000000000, 11111111111111... têm dígitos "corretos" mas não são CNPJs
    IF REPLACE(p_cnpj, LEFT(p_cnpj, 1), '') = '' THEN
        RETURN 0;
    END IF;

    -- 1º dígito: pesos 5,4,3,2,9,8,7,6,5,4,3,2 sobre os 12 primeiros dígitos
    WHILE i <= 12 DO
        SET soma = soma + CAST(SUBSTRING(p_cnpj, i, 1) AS UNSIGNED) * (((12 - i) MOD 8) + 2);
        SET i = i + 1;
    END WHILE;
    SET resto = soma MOD 11;
    SET dv1 = IF(resto < 2, 0, 11 - resto);

    -- 2º dígito: pesos 6,5,4,3,2,9,8,7,6,5,4,3,2 sobre os 13 primeiros dígitos
    SET i = 1;
    SET soma = 0;
    WHILE i <= 13 DO
        SET soma = soma + CAST(SUBSTRING(p_cnpj, i, 1) AS UNSIGNED) * (((13 - i) MOD 8) + 2);
        SET i = i + 1;
    END WHILE;
    SET resto = soma MOD 11;
    SET dv2 = IF(resto < 2, 0, 11 - resto);

    RETURN dv1 = CAST(SUBSTRING(p_cnpj, 13, 1) AS UNSIGNED)
       AND dv2 = CAST(SUBSTRING(p_cnpj, 14, 1) AS UNSIGNED);
END$$

CREATE TRIGGER trg_empresa_usuaria_cnpj_ins
BEFORE INSERT ON empresa_usuaria
FOR EACH ROW
BEGIN
    IF fn_cnpj_valido(NEW.cnpj) = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'CNPJ da empresa usuaria com digitos verificadores invalidos';
    END IF;
END$$

CREATE TRIGGER trg_empresa_usuaria_cnpj_upd
BEFORE UPDATE ON empresa_usuaria
FOR EACH ROW
BEGIN
    IF fn_cnpj_valido(NEW.cnpj) = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'CNPJ da empresa usuaria com digitos verificadores invalidos';
    END IF;
END$$

DELIMITER ;

-- =========================================================================
-- View
-- =========================================================================

-- Total de leads não é armazenado: é derivado por contagem.
CREATE VIEW vw_prospeccao_resumo AS
SELECT p.id            AS prospeccao_id,
       p.perfil_id,
       p.executada_em,
       p.status,
       p.total_empresas_avaliadas,
       COUNT(l.cnpj)   AS total_leads
FROM prospeccao p
LEFT JOIN `lead` l ON l.prospeccao_id = p.id
GROUP BY p.id;


-- Dados mínimos de domínio usados pelo repositório MySQL.
-- São códigos reais da Receita Federal, em quantidade reduzida: NÃO
-- substituem a carga completa das tabelas de código.
-- Pode ser rodado várias vezes.

-- '00' e '0000' NÃO são códigos da Receita: são marcadores de "não informado",
-- usados quando a Empresa não traz o dado (ver src/persistencia/marcadores.py).
INSERT INTO situacao_cadastral (codigo, descricao) VALUES
    ('00', 'NÃO INFORMADA'),
    ('01', 'NULA'),
    ('02', 'ATIVA'),
    ('03', 'SUSPENSA'),
    ('04', 'INAPTA'),
    ('08', 'BAIXADA')
ON DUPLICATE KEY UPDATE codigo = codigo;

INSERT INTO motivo_situacao (codigo, descricao) VALUES
    ('00', 'SEM MOTIVO')
ON DUPLICATE KEY UPDATE codigo = codigo;

INSERT INTO natureza_juridica (codigo, descricao) VALUES
    ('0000', 'NÃO INFORMADA'),
    ('2062', 'Sociedade Empresária Limitada')
ON DUPLICATE KEY UPDATE codigo = codigo;

-- Empresa usuária usada quando o repositório é criado sem informar
-- empresa_usuaria_id. É um SUBSTITUTO PROVISÓRIO: nome e e-mail não são reais e
-- o CNPJ só tem dígitos verificadores corretos (não foi tirado de uma empresa).
-- Troque pelos dados da empresa usuária verdadeira quando houver cadastro.
INSERT INTO empresa_usuaria (nome, cnpj, email) VALUES
    ('Empresa usuária padrão', '12345678000195', 'padrao@radarlead.invalid')
ON DUPLICATE KEY UPDATE cnpj = cnpj;


-- Municípios e CNAEs usados pelas empresas FICTÍCIAS de src/api/dados_exemplo.py
-- (python -m src.api --demo). Rode DEPOIS de schema.sql e seed_dominios.sql.
-- Pode ser rodado várias vezes. Não substitui a carga real dos municípios/CNAEs.
INSERT INTO municipio (codigo_ibge, nome, uf) VALUES
    ('5208707', 'Goiânia', 'GO'),
    ('5205109', 'Catalão', 'GO')
ON DUPLICATE KEY UPDATE codigo_ibge = codigo_ibge;

INSERT INTO cnae (codigo, descricao) VALUES
    ('6204000', 'Consultoria em tecnologia da informação'),
    ('5611201', 'Restaurantes e similares'),
    ('4520001', 'Manutenção e reparação mecânica de veículos')
ON DUPLICATE KEY UPDATE codigo = codigo;

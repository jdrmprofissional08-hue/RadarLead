-- Dados mínimos de domínio usados pelo repositório PostgreSQL.
-- São códigos reais da Receita Federal, em quantidade reduzida: NÃO
-- substituem a carga completa das tabelas de código (ver seção 3.4, item k).
-- Pode ser rodado várias vezes.

INSERT INTO situacao_cadastral (codigo, descricao) VALUES
    ('01', 'NULA'),
    ('02', 'ATIVA'),
    ('03', 'SUSPENSA'),
    ('04', 'INAPTA'),
    ('08', 'BAIXADA')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO motivo_situacao (codigo, descricao) VALUES
    ('00', 'SEM MOTIVO')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO natureza_juridica (codigo, descricao) VALUES
    ('2062', 'Sociedade Empresária Limitada')
ON CONFLICT (codigo) DO NOTHING;

-- Empresa usuária usada quando o repositório PostgreSQL é criado sem informar
-- empresa_usuaria_id. É um SUBSTITUTO PROVISÓRIO: CNPJ e e-mail não são reais.
-- Troque pelos dados da empresa usuária verdadeira quando houver cadastro.
INSERT INTO empresa_usuaria (nome, cnpj, email) VALUES
    ('Empresa usuária padrão', '00000000000000', 'padrao@radarlead.invalid')
ON CONFLICT (cnpj) DO NOTHING;

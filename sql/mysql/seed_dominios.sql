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

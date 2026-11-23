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

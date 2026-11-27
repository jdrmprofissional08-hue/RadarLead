-- Usuários individuais do grupo. Rode como root no servidor.
-- Troque SENHA_* por senhas fortes, UMA para cada pessoa, passadas em canal
-- privado. NUNCA coloque senhas reais no repositório.
-- '100.%' = só IPs da rede Tailscale (100.64.0.0/10); a porta NÃO é exposta na internet.
CREATE USER IF NOT EXISTS 'mateus'@'100.%'   IDENTIFIED BY 'SENHA_MATEUS';
CREATE USER IF NOT EXISTS 'eduardo'@'100.%'  IDENTIFIED BY 'SENHA_EDUARDO';
CREATE USER IF NOT EXISTS 'jose'@'100.%'     IDENTIFIED BY 'SENHA_JOSE';
CREATE USER IF NOT EXISTS 'mouhamed'@'100.%' IDENTIFIED BY 'SENHA_MOUHAMED';

-- consultar, alterar dados e criar/alterar objetos SÓ no banco radarlead
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX,
      REFERENCES, CREATE VIEW, SHOW VIEW, TRIGGER, EXECUTE,
      CREATE ROUTINE, ALTER ROUTINE
   ON radarlead.* TO 'mateus'@'100.%', 'eduardo'@'100.%', 'jose'@'100.%', 'mouhamed'@'100.%';
FLUSH PRIVILEGES;

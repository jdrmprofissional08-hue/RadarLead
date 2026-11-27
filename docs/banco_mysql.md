# Banco MySQL do RadarLead: acesso compartilhado e importação

Há dois jeitos de usar o banco:

- **Banco compartilhado do grupo** (um PC com MySQL, acessado por VPN privada): para trabalhar junto.
- **Cópia independente** (`sql/mysql/radarlead_completo.sql`): para o professor importar sem depender do nosso servidor.

## 1. Importar a cópia completa (professor ou qualquer integrante)

Requer MySQL 8.0.19 ou superior.

```
mysql -u root -p < sql/mysql/radarlead_completo.sql
```

No Workbench: *File > Run SQL Script...* e escolha o arquivo. Ele **apaga e recria** o banco `radarlead`
(15 tabelas, view `vw_prospeccao_resumo`, função `fn_cnpj_valido`, 2 triggers, domínios, 2 municípios e 3 CNAEs de demonstração).
Verificado: importa do zero e pode ser reimportado.

O arquivo é gerado por `schema.sql` + `seed_dominios.sql` + `seed_demo.sql`. Se mudar o schema, regenere:

```
cat cabecalho schema.sql seed_dominios.sql seed_demo.sql > radarlead_completo.sql
```

(o cabeçalho tem `DROP DATABASE IF EXISTS radarlead; CREATE DATABASE radarlead CHARACTER SET utf8mb4; USE radarlead;`).

Dados reais (empresas da Receita, catálogo completo do IBGE/CNAE) **não** estão no arquivo: são carregados pelo importador.

## 2. Banco compartilhado (no PC de quem hospeda)

### 2.1 Rede privada com Tailscale (sem abrir a porta 3306 na internet)
1. Todos criam conta e instalam o Tailscale (https://tailscale.com/download).
2. Quem hospeda convida os outros três para a mesma rede (tailnet, *Share* / *Invite users*).
3. No PC do servidor, `tailscale ip -4` mostra o endereço privado (`100.x.y.z`). Esse é o endereço que se passa ao grupo.
4. **Não** faça redirecionamento de porta no roteador. Não abra a 3306 no firewall para a internet.

### 2.2 Configurar o MySQL para aceitar a rede privada
No `my.ini` (Windows: `C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`), na seção `[mysqld]`:

```
bind-address = 0.0.0.0
port = 3306
```

Reinicie o serviço MySQL. Para que só o Tailscale alcance a porta, no PowerShell como administrador:

```
New-NetFirewallRule -DisplayName "MySQL Tailscale" -Direction Inbound -Protocol TCP -LocalPort 3306 -RemoteAddress 100.64.0.0/10 -Action Allow
```

Se existir regra antiga liberando a 3306 para qualquer origem, desative-a.

### 2.3 Usuários individuais
Edite `sql/mysql/usuarios.sql`, troque os `SENHA_*` por senhas fortes e rode como root. Cada pessoa recebe
sua senha em canal privado (**nunca** no repositório). Os usuários só conectam de IPs `100.%` e só têm
permissão no banco `radarlead`.

### 2.4 Conectar
Workbench: *Hostname* = endereço `100.x.y.z`, *Port* = 3306, *Username* = seu usuário.

Backend:

```
$env:RADARLEAD_MYSQL_URL = "mysql://SEU_USUARIO:SUA_SENHA@100.x.y.z:3306/radarlead"
python -m src.api
```

Se a senha tiver caracteres especiais (`@`, `:`, `/`), codifique-os na URL (`@` vira `%40`).

### 2.5 Limitações
- O banco só responde enquanto o PC do host estiver ligado, com MySQL e Tailscale ativos.
- Antes de mudanças de estrutura, avise o grupo e salve um backup:
  `mysqldump -u root -p --routines --triggers radarlead > backup.sql`.
- O arquivo do GitHub é a versão de entrega: depois de mudanças combinadas no banco compartilhado,
  atualize `schema.sql` (e regenere o `radarlead_completo.sql`) e faça commit.

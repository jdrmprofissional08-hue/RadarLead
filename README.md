# RadarLead
RadarLead é um sistema inteligente de prospecção comercial desenvolvido para identificar potenciais clientes (leads) de acordo com o perfil de produtos ou serviços oferecidos por uma empresa.  A aplicação integra dados empresariais da BrasilAPI (CNPJ e CEP), geolocalização e um classificador desenvolvido em Python para analisar a compatibilidade


## Persistência

O serviço depende só da interface `Repositorio` (`src/persistencia/repositorio.py`); há três implementações:

| Implementação | Arquivo | Uso |
|---|---|---|
| Memória | `repositorio_memoria.py` | desenvolvimento e testes |
| JSON | `repositorio_json.py` | persistência simples em arquivo |
| **MySQL** | `repositorio_mysql.py` | **banco do projeto** (esquema da Entrega 2; é o que a professora usa) |
| PostgreSQL | `repositorio_postgres.py` | alternativa (mesmo esquema) |

### MySQL (banco do projeto)

Requer MySQL **8.0.19 ou superior**.

```bash
pip install -r requirements.txt
mysql -u root -p -e "CREATE DATABASE radarlead CHARACTER SET utf8mb4"
mysql -u root -p radarlead < sql/mysql/schema.sql          # 15 tabelas + 1 view + função e triggers do CNPJ
mysql -u root -p radarlead < sql/mysql/seed_dominios.sql   # códigos mínimos + empresa usuária padrão
```

No MySQL Workbench: crie o schema `radarlead`, dê duplo clique nele e use *File > Run SQL Script...* com os dois arquivos (nesta ordem).

```python
from src.persistencia.conexao_mysql import GerenciadorConexaoMySQL
from src.persistencia.repositorio_mysql import RepositorioMySQL

repo = RepositorioMySQL(GerenciadorConexaoMySQL("mysql://usuario:senha@localhost:3306/radarlead"))
```

Senha com caracteres especiais vai codificada na URL (`@` = `%40`). O comportamento é o mesmo do PostgreSQL (veja abaixo): marcadores de "não informado", tabelas de código que precisam estar carregadas, mesmas limitações. Diferenças do MySQL: nomes de perfil iguais ignorando maiúsculas/acentos contam como duplicados, e o CNPJ da empresa usuária é conferido (dígitos verificadores) por um trigger, como no Quadro 1 do documento.

### PostgreSQL

```bash
pip install -r requirements.txt
createdb radarlead
psql -d radarlead -f sql/schema.sql          # 15 tabelas + 1 view
psql -d radarlead -f sql/seed_dominios.sql   # códigos mínimos (situação, motivo, natureza) + empresa usuária padrão
```

```python
from src.persistencia.conexao import GerenciadorConexao
from src.persistencia.repositorio_postgres import RepositorioPostgres

repo = RepositorioPostgres(GerenciadorConexao("host=localhost dbname=radarlead user=... password=..."))
```

`GerenciadorConexao` é um gerenciador de contexto: `with` abre a conexão, faz **commit** ao sair sem erro e **rollback** se houver erro; também expõe `commit()`/`rollback()` manuais. Falhas de conexão viram `PersistenciaError`.

**Antes de usar**: as tabelas de código (município, CNAE, situação, motivo, natureza jurídica) precisam estar carregadas; o repositório não inventa descrições. Se faltar um código, a gravação falha dizendo qual.

**Dados cadastrais** (situação, natureza jurídica, capital, datas): se a `Empresa` os traz, são gravados; se não, o banco recebe um **marcador** de "não informado" (`src/persistencia/marcadores.py`: situação `00`, natureza `0000`, datas `1900-01-01`, capital `0`) que volta como `None` ao ler — "desconhecido" nunca vira "ativa". Um `None` nunca apaga um dado que já esteja no banco. Perfis sem `empresa_usuaria_id` pertencem a uma "Empresa usuária padrão" (nome e e-mail fictícios; só para desenvolvimento).

**Limitações em relação à memória/JSON** (por causa do esquema): CNAEs voltam ordenados; `listar_empresas` ordena por CNPJ; leads voltam por pontuação (maior primeiro); pesos e pontuação guardam 2 casas decimais; uma justificativa não pode ter quebra de linha; toda `Empresa` precisa de CEP (o município vem do CEP). `prospeccao.total_empresas_avaliadas` é uma coluna acrescentada pelo grupo ao esquema do documento.

### Mudanças no domínio por causa do esquema

`Perfil`: `peso_cnae` virou `peso_segmento` (`peso_cnae` continua como propriedade e no `to_dict`); os três pesos precisam somar 100 (máx. 2 casas); novos `capital_minimo` (padrão 0) e `empresa_usuaria_id` (opcional). `Lead`: pontuação de 0 a 100. `Prospeccao`: novo `status` (`em_andamento`, `concluida`, `erro`; padrão `concluida`).

## API HTTP (para o frontend)

```bash
python -m src.api --demo        # http://127.0.0.1:8000, dados em memória + empresas fictícias
```

Com MySQL: defina `RADARLEAD_MYSQL_URL` antes (ex.: `$env:RADARLEAD_MYSQL_URL = "mysql://root:senha@localhost:3306/radarlead"`). Rota principal: `POST /api/prospeccoes` (perfil completo -> leads). Contrato, erros, CORS e variáveis de ambiente em [`docs/contrato_api.md`](docs/contrato_api.md). A prospecção usa o pipeline de `src/Recomendadores` (precisa estar no repositório).

## Testes

```bash
python -m unittest tests.testes_dominio tests.testes_servicos tests.testes_repositorio \
    tests.testes_repositorio_json tests.testes_conexao tests.testes_repositorio_postgres \
    tests.testes_conexao_mysql tests.testes_repositorio_mysql tests.testes_api
```

Os testes que usam PostgreSQL de verdade só rodam se `RADARLEAD_TEST_DSN` apontar para um banco de **teste** (ex.: `export RADARLEAD_TEST_DSN="host=localhost dbname=radarlead_teste user=... password=..."`); sem ela são pulados. Tudo acontece no schema `radarlead_teste`, criado e removido pelos próprios testes; o schema `public` não é tocado.

Os testes do MySQL só rodam com `RADARLEAD_TEST_MYSQL_URL` apontando para um **servidor** de teste, sem nome de banco (ex.: `$env:RADARLEAD_TEST_MYSQL_URL = "mysql://root:senha@localhost:3306"`); tudo acontece no banco `radarlead_teste`, criado e removido pelos testes. Os testes do pipeline real (`TestPipelineDoJose`) são pulados enquanto `src/Recomendadores` não estiver no repositório.

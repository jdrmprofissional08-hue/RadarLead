# RadarLead
RadarLead é um sistema inteligente de prospecção comercial desenvolvido para identificar potenciais clientes (leads) de acordo com o perfil de produtos ou serviços oferecidos por uma empresa.  A aplicação integra dados empresariais da BrasilAPI (CNPJ e CEP), geolocalização e um classificador desenvolvido em Python para analisar a compatibilidade


## Persistência

O serviço depende só da interface `Repositorio` (`src/persistencia/repositorio.py`); há três implementações:

| Implementação | Arquivo | Uso |
|---|---|---|
| Memória | `repositorio_memoria.py` | desenvolvimento e testes |
| JSON | `repositorio_json.py` | persistência simples em arquivo |
| PostgreSQL | `repositorio_postgres.py` | banco do projeto (esquema da Entrega 2) |

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

**Substitutos provisórios** (o domínio atual não tem esses dados, mas o esquema exige): natureza jurídica, capital social, situação, motivo e datas de situação/início de atividade recebem valores padrão na primeira gravação de uma empresa (constantes `PADRAO_*` em `repositorio_postgres.py`; data `1900-01-01` = desconhecida) e **nunca sobrescrevem** dados já carregados. Perfis sem `empresa_usuaria_id` pertencem a uma "Empresa usuária padrão" (CNPJ e e-mail fictícios, só para desenvolvimento).

**Limitações em relação à memória/JSON** (por causa do esquema): CNAEs voltam ordenados; `listar_empresas` ordena por CNPJ; leads voltam por pontuação (maior primeiro); pesos e pontuação guardam 2 casas decimais; uma justificativa não pode ter quebra de linha; toda `Empresa` precisa de CEP (o município vem do CEP). `prospeccao.total_empresas_avaliadas` é uma coluna acrescentada pelo grupo ao esquema do documento.

### Mudanças no domínio por causa do esquema

`Perfil`: `peso_cnae` virou `peso_segmento` (`peso_cnae` continua como propriedade e no `to_dict`); os três pesos precisam somar 100 (máx. 2 casas); novos `capital_minimo` (padrão 0) e `empresa_usuaria_id` (opcional). `Lead`: pontuação de 0 a 100. `Prospeccao`: novo `status` (`em_andamento`, `concluida`, `erro`; padrão `concluida`).

## Testes

```bash
python -m unittest tests.testes_dominio tests.testes_servicos tests.testes_repositorio \
    tests.testes_repositorio_json tests.testes_conexao tests.testes_repositorio_postgres
```

Os testes que usam PostgreSQL de verdade só rodam se `RADARLEAD_TEST_DSN` apontar para um banco de **teste** (ex.: `export RADARLEAD_TEST_DSN="host=localhost dbname=radarlead_teste user=... password=..."`); sem ela são pulados. Tudo acontece no schema `radarlead_teste`, criado e removido pelos próprios testes; o schema `public` não é tocado.

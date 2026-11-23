# Contrato da API HTTP do RadarLead — v1.0

Servidor Flask. Em desenvolvimento: `http://127.0.0.1:8000`. Tudo em JSON UTF-8.

## Como iniciar

```bash
pip install -r requirements.txt
python -m src.api --demo          # dados em memória + empresas fictícias
```

Com MySQL (os dados persistem; ver README):

```powershell
$env:RADARLEAD_MYSQL_URL = "mysql://usuario:senha@localhost:3306/radarlead"
python -m src.api
```

| Opção / variável | Padrão | Para quê |
|---|---|---|
| `--host`, `--porta` | `127.0.0.1`, `8000` | onde o servidor escuta |
| `--demo` | desligado | carrega 6 empresas **fictícias** (ver `src/api/dados_exemplo.py`) |
| `RADARLEAD_MYSQL_URL` | vazio (memória) | banco MySQL; sem ele os dados somem ao parar |
| `RADARLEAD_CORS_ORIGENS` | `http://localhost:5173,http://127.0.0.1:5173` | origens do frontend liberadas (`*` libera todas) |
| `RADARLEAD_FORNECEDOR_LAT` / `_LON` | Goiânia (-16.6799 / -49.2550) | ponto de origem da busca |
| `RADARLEAD_RAIO_KM` | `350` | raio máximo (km) até a empresa; máximo 350 |

CORS: já liberado para o Vite (`http://localhost:5173` e `http://127.0.0.1:5173`), com preflight (`OPTIONS`).

## Rota principal

### `POST /api/prospeccoes`

Recebe o perfil completo, grava (ou atualiza) o perfil, executa a prospecção e devolve os leads **em uma única chamada**.

Corpo:

```json
{
  "nome": "TI em Goiânia",
  "cnaes_desejados": ["6204000"],
  "porte_desejado": 3,
  "municipio_alvo_ibge": "5208707",
  "peso_cnae": 50,
  "peso_porte": 25,
  "peso_localizacao": 25
}
```

| Campo | Regra |
|---|---|
| `nome` | obrigatório, texto. Se já existir um perfil com o mesmo nome (ignorando maiúsculas e espaços nas pontas), ele é **atualizado** — não duplica |
| `cnaes_desejados` | obrigatório, lista com ao menos 1 CNAE de 7 dígitos |
| `porte_desejado` | obrigatório: `0` não informado, `1` microempresa, `3` pequeno porte, `5` demais |
| `municipio_alvo_ibge` | obrigatório, código IBGE de 7 dígitos |
| `peso_cnae` (ou `peso_segmento`) | opcional, padrão 50 |
| `peso_porte` | opcional, padrão 25 |
| `peso_localizacao` | opcional, padrão 25 |
| `capital_minimo` | opcional, padrão 0 |

Os três pesos **precisam somar 100** (cada um entre 0 e 100).

Resposta — `201 Created`:

```json
{
  "id": 1,
  "perfil_id": 1,
  "status": "concluida",
  "criada_em": "2026-11-23T07:13:09.261089",
  "total_empresas_avaliadas": 6,
  "total_leads": 3,
  "perfil": { "id": 1, "nome": "TI em Goiânia", "cnaes_desejados": ["6204000"], "porte_desejado": 3,
              "municipio_alvo_ibge": "5208707", "peso_segmento": 50, "peso_cnae": 50,
              "peso_porte": 25, "peso_localizacao": 25, "capital_minimo": 0, "empresa_usuaria_id": 1 },
  "leads": [
    {
      "cnpj": "11111111000100",
      "razao_social": "Alfa Sistemas Demonstração Ltda",
      "pontuacao": 100,
      "justificativas": ["CNAE compatível: +50 pontos", "Porte compatível: +25 pontos", "Município compatível: +25 pontos"],
      "status": "novo",
      "cnae_principal": "6204000",
      "porte": 3,
      "porte_descricao": "Empresa de pequeno porte",
      "municipio_ibge": "5208707"
    }
  ]
}
```

- `leads` vem **ordenado por `pontuacao`, do maior para o menor**; `pontuacao` vai de 0 a 100.
- `justificativas` é sempre uma lista de textos (pode ser vazia).
- Para o nome do município, o frontend deve mapear `municipio_ibge` (a API só devolve o código).
- **Resultado vazio não é erro:** vem `201` com `"leads": []` e `"total_leads": 0`. Mostre "nenhuma empresa encontrada".

## Rotas de consulta

| Rota | Resposta |
|---|---|
| `GET /api/saude` | `{"status": "ok"}` |
| `GET /api/prospeccoes` | `{"prospeccoes": [...]}` — mesmos campos de cima, **sem** `leads` (com `total_leads`). Filtro opcional: `?perfil_id=1` |
| `GET /api/prospeccoes/<id>` | uma prospecção completa, igual à resposta do POST (`200`) |
| `GET /api/perfis` | `{"perfis": [...]}` |

## Erros

Todo erro tem o mesmo formato, e a `mensagem` pode ser exibida ao usuário:

```json
{ "erro": { "codigo": "dados_invalidos", "mensagem": "Os pesos devem somar 100 ..." } }
```

| HTTP | `codigo` | Quando |
|---|---|---|
| 400 | `json_invalido` | corpo vazio, que não é JSON ou que não é um objeto |
| 400 | `dados_invalidos` | campo ausente, tipo errado, pesos que não somam 100, porte fora de 0/1/3/5, CNAE ou IBGE malformado |
| 404 | `nao_encontrado` | prospecção/perfil inexistente |
| 404 | `rota_inexistente` | URL que não existe |
| 405 | `metodo_nao_permitido` | método HTTP errado para a rota |
| 502 | `falha_na_prospeccao` | o recomendador falhou ou respondeu fora do contrato |
| 503 | `banco_indisponivel` | o banco de dados não respondeu |
| 500 | `erro_interno` | erro inesperado (sem detalhes técnicos na resposta) |

Nada é gravado quando o perfil é inválido (400).

## Observações

- Só entram como leads empresas **ativas** (situação cadastral 2), com CEP e coordenadas, com algum CNAE (principal ou secundário) entre os desejados e dentro do raio configurado.
- A pontuação é a soma dos pesos dos critérios atendidos (CNAE, porte, município).
- As requisições são atendidas uma por vez.

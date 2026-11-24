# Coordenadas de referência dos municípios

Fonte: IBGE, Censo Demográfico 2022 — Localidades do Brasil. Pontos de referência extraídos e adaptados do GeoPackage nacional. Divulgação em 24/11/2025, arquivo obtido em 24/11/2026.

- [Arquivo oficial](https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/localidades/Localidades_do_Brasil/2022/Localidades_Brasil_gpkg.zip)
- SHA-256 do ZIP: `1d96d5f0b379972a506d4b18c3696af974fbe59f8f6680557cb3a6dd38a0eb57`
- SHA-256 do membro `BR_localidades_2022.gpkg`: `d057a1638b16257f17338ea2b8a4fc1e0b4b4b93012c5a7fa294f44e401e2704`
- SHA-256 do JSON: `87e532da4ddd8b6bf6599ac269efb57574107ec007ee4e01a90957d9ad487743`

O gerador lê a geometria POINT em SIRGAS 2000 (EPSG:4674), com X como longitude e Y como latitude. Preserva o referencial, arredonda a até seis casas e gera um objeto ordenado por código textual com valores `[latitude, longitude]`.

São selecionadas as subcategorias Sede Municipal, Capital Estadual e Capital Federal da categoria Cidade, mais o Distrito Estadual de Fernando de Noronha. Brasília entra como Capital Federal, sem as regiões administrativas. São 5.597 candidatos e 26 códigos com pares de registros com a mesma coordenada. A consolidação compara os valores originais antes de arredondar. O cruzamento por código com `municipios.json` confirma 5.571 correspondências, sem ausentes ou adicionais. Os nomes usados na interface vêm do catálogo municipal. A fonte pontual usa Governador Edison Lobão para o atual Ribeirãozinho do Maranhão (2104552) e Bom Jesus para Bom Jesus de Goiás (5203500).

Cobertura de 100% em cada UF (contagem por UF):

- Norte: AC 22, AM 62, AP 16, PA 144, RO 52, RR 15, TO 139.
- Nordeste: AL 102, BA 417, CE 184, MA 217, PB 223, PE 185, PI 224, RN 167, SE 75.
- Centro-Oeste: DF 1, GO 246, MS 79, MT 142.
- Sudeste: ES 78, MG 853, RJ 92, SP 645.
- Sul: PR 399, RS 497, SC 295.

O ponto da sede é uma referência e sua exatidão depende da fonte. O arredondamento não melhora a exatidão. O pipeline usa Haversine para estimar distância em linha reta sobre uma esfera, sem considerar o trajeto rodoviário.

## Geração local

Baixe o ZIP oficial para uma pasta fora dos worktrees. A partir de `frontend/`, com Python 3 e sua biblioteca padrão:

```bash
python3 scripts/gerar-coordenadas-municipios.py /caminho/externo/Localidades_Brasil_gpkg.zip
npm run dev
```

Abra o frontend em loopback no modo HTTP. A opção de município de origem carrega o JSON de `.dados-locais/` sob demanda, pela rota do mesmo servidor Vite, respeitando o caminho-base. O modo simulado, a configuração do servidor e as coordenadas manuais funcionam sem o arquivo.

O JSON permanece fora do Git. O servidor de desenvolvimento aceita servir o arquivo somente a conexões de loopback. O arquivo fica fora de `public/`, o plugin só registra a rota no servidor de desenvolvimento e `npm run build` gera `dist/` sem o catálogo, mesmo depois da geração local. Um build servido por `vite preview` também fica sem catálogo. O build e os testes funcionam sem baixar a fonte. Para testar o gerador com entradas sintéticas, execute `python3 tests/test_gerar_coordenadas.py` em `frontend/`.

A confirmação documental das condições de redistribuição continua pendente. Mantenha o JSON fora de commits, builds públicos, releases e outros artefatos distribuídos. A geração em cada ambiente local não concede permissão de redistribuição.

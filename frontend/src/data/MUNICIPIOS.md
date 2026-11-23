# Catálogo de municípios

Fonte: [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/v1/localidades/municipios).
Resposta obtida em **23/11/2026**, com **5.571 registros**.
SHA-256 da resposta: `cf005d0277172793bc3c3409a926aeae307dff6a3468d75c7edf8ffb7b49cf7a`.

Para atualizar, execute a partir da raiz do worktree:

```bash
curl -fLsS https://servicodados.ibge.gov.br/api/v1/localidades/municipios -o /tmp/municipios-ibge.json
python3 -B frontend/scripts/gerar-municipios.py /tmp/municipios-ibge.json
sha256sum /tmp/municipios-ibge.json
```

Revise a quantidade, as diferenças e a versão carregada no MySQL. Atualize a data e o checksum neste documento. O script usa a região imediata ou a microrregião para identificar a UF e preserva o código IBGE como texto. O seed de demonstração do backend inclui Goiânia e Catalão. A chave estrangeira da tabela de perfis exige que o município escolhido também esteja na carga do banco.

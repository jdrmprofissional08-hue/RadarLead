# Catálogo CNAE

O catálogo contém as 1.332 subclasses da CNAE-Subclasses 2.3 do IBGE/CONCLA.
A fonte é a planilha **Estrutura Detalhada** do [arquivo ODS oficial](https://ftp.ibge.gov.br/Informacoes_Gerais_e_Referencia/Classificacoes/CNAE/cnae2_3/cnae_subclasses_2_3_ods.zip), obtido em 23/11/2026.
SHA-256 do ZIP: `656685fb58ab46eb3d63d571b4acb1cb13a8a4332fb79bae9afbc538fd681f08`.

Para atualizar a partir do ZIP oficial, execute na raiz do worktree:

```bash
python3 -B frontend/scripts/gerar-cnaes.py /caminho/para/cnae_subclasses_2_3_ods.zip
```

O script usa a biblioteca padrão do Python, preserva os códigos de sete dígitos como texto, verifica duplicatas e confere a contagem da versão 2.3. Em uma mudança de versão, confira a nova contagem oficial, revise o JSON e alinhe a carga da tabela `cnae` com o backend antes de publicar.

A pesquisa local encontra palavras das denominações oficiais. A base demo do banco contém apenas um recorte do catálogo.

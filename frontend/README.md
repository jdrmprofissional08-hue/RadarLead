# Frontend RadarLead

O modo HTTP permite escolher um ponto de referência municipal como origem da prospecção durante o desenvolvimento local. O catálogo é opcional. Consulte a [fonte oficial, os créditos e o procedimento de geração local](src/data/COORDENADAS_MUNICIPIOS.md).

Execute `npm run dev` para usar o catálogo gerado localmente em loopback. `npm run build` gera a versão de distribuição com a configuração de servidor e as coordenadas manuais disponíveis no modo HTTP. O catálogo local fica fora de `dist/` enquanto as condições de redistribuição estiverem pendentes.

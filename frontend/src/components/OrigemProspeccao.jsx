export default function OrigemProspeccao({ modoHttp, configuracao, onAlterar, atributosCampo, estiloCampo, renderizarErro }) {
  const campos = [
    { chave: 'latitude', rotulo: 'Latitude' },
    { chave: 'longitude', rotulo: 'Longitude' },
    ...(!configuracao.raioPadrao ? [{ chave: 'raio', rotulo: 'Raio (km)' }] : []),
  ]

  return (
    <fieldset className="min-w-0 space-y-3 rounded-lg border border-divisor p-4">
      <legend className="px-1 font-semibold text-marinho">Origem desta prospecção</legend>
      {modoHttp ? (
        <>
          <p className="text-sm text-suave">A origem é o ponto de partida para medir distância. O município-alvo é um critério separado do perfil.</p>
          <p className="text-sm text-suave">A origem vale somente para esta prospecção e não será armazenada no histórico.</p>
          <div className="space-y-2 text-sm">
            <label className="flex min-h-10 items-center gap-2">
              <input type="radio" name="modo-origem" checked={configuracao.modo === 'servidor'}
                onChange={() => onAlterar('modo', 'servidor')} />
              Usar configuração do servidor
            </label>
            <label className="flex min-h-10 items-center gap-2">
              <input type="radio" name="modo-origem" checked={configuracao.modo === 'manual'}
                onChange={() => onAlterar('modo', 'manual')} />
              Informar coordenadas manualmente
            </label>
          </div>
          {configuracao.modo === 'servidor' ? (
            <p className="text-sm text-suave">As coordenadas e o raio serão definidos pelo servidor.</p>
          ) : (
            <>
              <label className="flex min-h-10 items-center gap-2 text-sm">
                <input type="checkbox" checked={configuracao.raioPadrao}
                  onChange={(evento) => onAlterar('raioPadrao', evento.target.checked)} />
                Usar raio padrão do servidor
              </label>
              <p id="origem-ajuda" className="text-sm text-suave">Use ponto ou vírgula para decimais, sem separadores de milhares.</p>
              <div className="grid gap-4 sm:grid-cols-2">
                {campos.map(({ chave, rotulo }) => (
                  <div key={chave} className="min-w-0">
                    <label htmlFor={chave} className="mb-2 block text-sm font-semibold">{rotulo}</label>
                    <input {...atributosCampo(chave, 'origem-ajuda')} name={chave}
                      inputMode="decimal" required value={configuracao[chave]}
                      onChange={(evento) => onAlterar(chave, evento.target.value)} className={estiloCampo} />
                    {renderizarErro(chave)}
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      ) : (
        <p className="text-sm text-suave">A configuração de origem e raio personalizados depende da API real.</p>
      )}
    </fieldset>
  )
}

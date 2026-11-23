import { useEffect, useId, useRef, useState } from 'react'
export default function CampoPesquisa({
  atributos, estiloCampo, rotulo, ajuda, rotuloLista, semResultados,
  pesquisar, renderizarOpcao, onSelecionar, desabilitada = () => false,
  children,
}) {
  const campoId = atributos.id
  const [consulta, setConsulta] = useState('')
  const [aberta, setAberta] = useState(false)
  const [ativo, setAtivo] = useState(-1)
  const entrada = useRef(null)
  const opcaoAtiva = useRef(null)
  const listaId = useId()
  const opcoes = aberta ? pesquisar(consulta) : []
  const visivel = aberta && Boolean(consulta.trim())
  const expandida = visivel && opcoes.length > 0

  useEffect(() => {
    opcaoAtiva.current?.scrollIntoView?.({ block: 'nearest' })
  }, [ativo])

  function selecionar(codigo) {
    if (desabilitada(codigo)) return
    entrada.current.focus()
    setConsulta('')
    setAberta(false)
    setAtivo(-1)
    onSelecionar(codigo)
  }

  function teclado(evento) {
    if (evento.nativeEvent.isComposing) return

    switch (evento.key) {
      case 'Escape':
        if (aberta) evento.preventDefault()
        setAberta(false)
        setAtivo(-1)
        break
      case 'Enter':
        evento.preventDefault()
        if (opcoes[ativo]) selecionar(opcoes[ativo].codigo)
        break
      case 'ArrowDown':
      case 'ArrowUp': {
        if (!consulta.trim()) break
        evento.preventDefault()
        setAberta(true)
        const total = opcoes.length || pesquisar(consulta).length
        if (!total) break
        if (evento.key === 'ArrowDown') setAtivo((ativo + 1) % total)
        else setAtivo(ativo <= 0 ? total - 1 : ativo - 1)
        break
      }
    }
  }

  return (
    <div>
      <label htmlFor={campoId} className="mb-2 block text-sm font-medium">{rotulo}</label>
      <input
        {...atributos}
        ref={entrada}
        name={campoId}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={expandida}
        aria-controls={expandida ? listaId : undefined}
        aria-activedescendant={opcoes[ativo] ? `${listaId}-${ativo}` : undefined}
        autoComplete="off"
        value={consulta}
        onFocus={() => setAberta(true)}
        onBlur={() => { setAberta(false); setAtivo(-1) }}
        onChange={(evento) => {
          setConsulta(evento.target.value)
          setAberta(true)
          setAtivo(-1)
        }}
        onKeyDown={teclado}
        className={estiloCampo}
      />
      <p id={`${campoId}-ajuda`} className="mt-2 text-sm text-suave">
        {ajuda}
      </p>
      <p role="status" className={visivel && !expandida ? 'mt-2 text-sm text-suave' : 'sr-only'}>
        {visivel && (expandida ? `${opcoes.length} sugestões exibidas.` : semResultados)}
      </p>
      {expandida && (
        <ul id={listaId} role="listbox" aria-label={rotuloLista} className="mt-2 max-h-64 overflow-y-auto rounded-lg border border-divisor">
          {opcoes.map((opcao, indice) => {
            const { codigo } = opcao
            const selecionada = desabilitada(codigo)
            return (
              <li
                key={codigo}
                id={`${listaId}-${indice}`}
                ref={indice === ativo ? opcaoAtiva : undefined}
                role="option"
                aria-selected={indice === ativo}
                aria-disabled={selecionada}
                onMouseDown={(evento) => evento.preventDefault()}
                onClick={() => selecionar(codigo)}
                className={`flex min-h-11 flex-wrap items-center gap-x-2 border-b border-divisor px-3 py-2 text-sm last:border-0 ${indice === ativo ? 'bg-acao-suave' : 'hover:bg-fundo'} ${selecionada ? 'cursor-not-allowed text-suave' : 'cursor-pointer'}`}
              >
                {renderizarOpcao(opcao)}
                {selecionada && <span className="text-xs font-semibold">Já selecionada</span>}
              </li>
            )
          })}
        </ul>
      )}
      {children}
    </div>
  )
}

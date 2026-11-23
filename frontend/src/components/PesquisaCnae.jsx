import { useEffect, useId, useRef, useState } from 'react'
import { cnaesPorCodigo, formatarCnae, pesquisarCnaes } from '../utils/pesquisaCnae.js'

export default function PesquisaCnae({ selecionados, onAlterar, atributos, estiloCampo }) {
  const [consulta, setConsulta] = useState('')
  const [aberta, setAberta] = useState(false)
  const [ativo, setAtivo] = useState(-1)
  const entrada = useRef(null)
  const opcaoAtiva = useRef(null)
  const listaId = useId()
  const opcoes = aberta ? pesquisarCnaes(consulta) : []
  const visivel = aberta && Boolean(consulta.trim())
  const expandida = visivel && opcoes.length > 0

  useEffect(() => {
    opcaoAtiva.current?.scrollIntoView?.({ block: 'nearest' })
  }, [ativo])

  function selecionar(codigo) {
    if (selecionados.includes(codigo)) return
    entrada.current.focus()
    setConsulta('')
    setAberta(false)
    setAtivo(-1)
    onAlterar([...selecionados, codigo])
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
        const total = opcoes.length || pesquisarCnaes(consulta).length
        if (!total) break
        if (evento.key === 'ArrowDown') setAtivo((ativo + 1) % total)
        else setAtivo(ativo <= 0 ? total - 1 : ativo - 1)
        break
      }
    }
  }

  return (
    <div>
      <label htmlFor="cnae" className="mb-2 block text-sm font-medium">Pesquisar por atividade ou código CNAE</label>
      <input
        {...atributos}
        ref={entrada}
        name="cnae"
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
      <p id="cnae-ajuda" className="mt-2 text-sm text-suave">
        Selecione pelo menos uma atividade. Use as setas e Enter para selecionar ou Escape para fechar.
      </p>
      <p role="status" className={visivel && !expandida ? 'mt-2 text-sm text-suave' : 'sr-only'}>
        {visivel && (expandida ? `${opcoes.length} sugestões exibidas.` : 'Nenhuma atividade encontrada.')}
      </p>
      {expandida && (
        <ul id={listaId} role="listbox" aria-label="Sugestões de CNAE" className="mt-2 max-h-64 overflow-y-auto rounded-lg border border-divisor">
          {opcoes.map(({ codigo, descricao }, indice) => {
            const selecionada = selecionados.includes(codigo)
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
                <strong>{formatarCnae(codigo)}</strong>
                <span>{descricao}</span>
                {selecionada && <span className="text-xs font-semibold">Já selecionada</span>}
              </li>
            )
          })}
        </ul>
      )}
      {selecionados.length > 0 && (
        <ul aria-label="CNAEs adicionados" className="mt-3 flex flex-wrap gap-2">
          {selecionados.map((codigo) => (
            <li key={codigo} className="max-w-full">
              <button
                type="button"
                aria-label={`Remover CNAE ${codigo}, ${cnaesPorCodigo.get(codigo).descricao}`}
                onClick={() => {
                  entrada.current.focus()
                  onAlterar(selecionados.filter((atual) => atual !== codigo))
                }}
                className="min-h-11 rounded-lg bg-fundo px-3 py-2 text-left text-sm text-texto hover:bg-acao-suave hover:text-acao"
              >
                <strong>{formatarCnae(codigo)}</strong> · {cnaesPorCodigo.get(codigo).descricao} <span aria-hidden="true">×</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

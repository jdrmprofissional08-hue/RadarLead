import { useState } from 'react'
import {
  criterios,
  municipiosProvisorios,
  portesProvisorios,
  prepararCnae,
  totalizarPesos,
  validarPerfil,
} from '../utils/perfilProspeccao.js'

const estiloCampo = 'w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400 aria-invalid:border-rose-400'
const estiloBotao = 'rounded-md px-3 py-2 font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400'
const formatoTotal = new Intl.NumberFormat('pt-BR', { maximumSignificantDigits: 15 })

function ErroCampo({ campo, mensagem }) {
  return mensagem && (
    <p id={`${campo}-erro`} className="mt-1 text-sm text-rose-300">
      {mensagem}
    </p>
  )
}

export default function FormularioPerfil() {
  const [cnae, setCnae] = useState('')
  const [cnaes, setCnaes] = useState([])
  const [porte, setPorte] = useState('')
  const [municipio, setMunicipio] = useState('')
  const [pesos, setPesos] = useState(() => Object.fromEntries(
    criterios.map(({ chave, inicial }) => [chave, inicial]),
  ))
  const [erros, setErros] = useState({})
  const [perfilValidado, setPerfilValidado] = useState(null)
  const total = totalizarPesos(pesos)

  function atributosCampo(campo, ajuda) {
    return {
      id: campo,
      'aria-invalid': Boolean(erros[campo]),
      'aria-describedby': [ajuda, erros[campo] && `${campo}-erro`].filter(Boolean).join(' ') || undefined,
    }
  }

  function limparValidacao(campo) {
    setErros((anteriores) => ({ ...anteriores, [campo]: undefined }))
    setPerfilValidado(null)
  }

  function adicionarCnae() {
    limparValidacao('cnae')
    const { codigo, erro } = prepararCnae(cnae, cnaes)
    if (erro) {
      setErros((anteriores) => ({ ...anteriores, cnae: erro }))
      return
    }
    setCnaes([...cnaes, codigo])
    setCnae('')
  }

  function removerCnae(codigo) {
    limparValidacao('cnae')
    setCnaes(cnaes.filter((atual) => atual !== codigo))
  }

  function enviar(evento) {
    evento.preventDefault()
    const resultado = validarPerfil({ cnaes, cnae, porte, municipio, pesos })
    setErros(resultado.erros ?? {})
    setPerfilValidado(resultado.perfilValidado ?? null)

    if (resultado.erros) {
      const primeiroCampo = Object.keys(resultado.erros)[0]
      evento.currentTarget.elements.namedItem(primeiroCampo)?.focus()
      return
    }

    setCnaes(resultado.perfilValidado.perfil.cnaes_desejados)
    setCnae('')
  }

  return (
    <form noValidate onSubmit={enviar} className="mt-8 max-w-3xl space-y-6">
      <fieldset className="min-w-0 space-y-3">
        <legend className="mb-2 font-semibold">CNAEs desejados</legend>
        <label htmlFor="cnae" className="block text-sm">Código CNAE</label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            {...atributosCampo('cnae', 'cnae-ajuda')}
            name="cnae"
            value={cnae}
            onChange={(evento) => {
              setCnae(evento.target.value)
              limparValidacao('cnae')
            }}
            onKeyDown={(evento) => {
              if (evento.key === 'Enter' && !evento.nativeEvent.isComposing) {
                evento.preventDefault()
                adicionarCnae()
              }
            }}
            className={estiloCampo}
          />
          <button type="button" onClick={adicionarCnae} className={`${estiloBotao} bg-slate-800 text-emerald-300 hover:bg-slate-700 sm:shrink-0`}>
            Adicionar CNAE
          </button>
        </div>
        <p id="cnae-ajuda" className="text-sm text-slate-400">
          Informe pelo menos um código. Exemplo: 6204000 ou 6204-0/00.
        </p>
        <div aria-live="polite">
          <ErroCampo campo="cnae" mensagem={erros.cnae} />
          {cnaes.length > 0 && (
            <ul aria-label="CNAEs adicionados" className="flex flex-wrap gap-2">
              {cnaes.map((codigo) => (
                <li key={codigo}>
                  <button
                    type="button"
                    onClick={() => removerCnae(codigo)}
                    className={`${estiloBotao} bg-slate-800 text-sm hover:bg-slate-700`}
                  >
                    Remover CNAE {codigo}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </fieldset>

      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          <label htmlFor="porte" className="mb-2 block font-semibold">Porte empresarial</label>
          <select
            {...atributosCampo('porte', 'porte-ajuda')}
            name="porte"
            required
            value={porte}
            onChange={(evento) => {
              setPorte(evento.target.value)
              limparValidacao('porte')
            }}
            className={estiloCampo}
          >
            <option value="">Selecione o porte</option>
            {portesProvisorios.map((codigo) => (
              <option key={codigo} value={codigo}>Código {codigo} (provisório)</option>
            ))}
          </select>
          <p id="porte-ajuda" className="mt-1 text-sm text-slate-400">Opções provisórias do classificador.</p>
          <ErroCampo campo="porte" mensagem={erros.porte} />
        </div>

        <div>
          <label htmlFor="municipio" className="mb-2 block font-semibold">Município-alvo</label>
          <select
            {...atributosCampo('municipio', 'municipio-ajuda')}
            name="municipio"
            required
            value={municipio}
            onChange={(evento) => {
              setMunicipio(evento.target.value)
              limparValidacao('municipio')
            }}
            className={estiloCampo}
          >
            <option value="">Selecione o município</option>
            {municipiosProvisorios.map(({ nome, uf, codigo }) => (
              <option key={codigo} value={codigo}>{nome} ({uf}) · {codigo}</option>
            ))}
          </select>
          <p id="municipio-ajuda" className="mt-1 text-sm text-slate-400">Lista provisória com códigos oficiais do IBGE.</p>
          <ErroCampo campo="municipio" mensagem={erros.municipio} />
        </div>
      </div>

      <fieldset className="min-w-0 space-y-3">
        <legend className="mb-2 font-semibold">Pesos dos critérios</legend>
        <div className="grid gap-4 sm:grid-cols-3">
          {criterios.map(({ chave, rotulo }) => (
            <div key={chave}>
              <label htmlFor={chave} className="mb-2 block text-sm">{rotulo}</label>
              <input
                {...atributosCampo(chave)}
                name={chave}
                type="number"
                min="0"
                step="any"
                required
                value={pesos[chave]}
                onChange={(evento) => {
                  setPesos({ ...pesos, [chave]: evento.target.value })
                  limparValidacao(chave)
                }}
                className={estiloCampo}
              />
              <ErroCampo campo={chave} mensagem={erros[chave]} />
            </div>
          ))}
        </div>
        <output htmlFor={criterios.map(({ chave }) => chave).join(' ')} className="block text-sm text-slate-300">
          Total dos pesos: {total === null ? 'indisponível' : formatoTotal.format(total)}
        </output>
      </fieldset>

      <button type="submit" className={`${estiloBotao} bg-emerald-400 text-slate-950 hover:bg-emerald-300`}>
        Validar perfil
      </button>
      <div role="status" className="text-sm text-emerald-300">
        {perfilValidado && 'Perfil validado com sucesso.'}
      </div>
    </form>
  )
}

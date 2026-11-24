import { useState } from 'react'
import ProdutoDoPerfil from './ProdutoDoPerfil.jsx'
import PesquisaCnae from './PesquisaCnae.jsx'
import PesquisaMunicipio from './PesquisaMunicipio.jsx'
import {
  criterios,
  portesPerfil,
  totalizarPesos,
  validarPerfil,
} from '../utils/perfilProspeccao.js'

const estiloCampo = 'w-full min-w-0 rounded-lg border border-controle bg-superficie px-3 py-2.5 text-texto aria-invalid:border-erro'
const estiloBotao = 'rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors'
const formatoTotal = new Intl.NumberFormat('pt-BR', { maximumSignificantDigits: 15 })

function ErroCampo({ campo, mensagem }) {
  return mensagem && (
    <p id={`${campo}-erro`} className="mt-2 text-sm font-medium text-erro">
      {mensagem}
    </p>
  )
}

export default function FormularioPerfil({ onBuscar, onAlterar, buscando, associacao }) {
  const [nome, setNome] = useState('')
  const [cnaes, setCnaes] = useState([])
  const [porte, setPorte] = useState('')
  const [municipio, setMunicipio] = useState('')
  const [pesos, setPesos] = useState(() => Object.fromEntries(
    criterios.map(({ chave, inicial }) => [chave, inicial]),
  ))
  const [erros, setErros] = useState({})
  const total = totalizarPesos(pesos)

  function atributosCampo(campo, ajuda) {
    return {
      id: campo,
      'aria-invalid': Boolean(erros[campo]),
      'aria-describedby': [ajuda, erros[campo] && `${campo}-erro`].filter(Boolean).join(' ') || undefined,
    }
  }

  function limparValidacao(campo, erroRelacionado) {
    setErros((anteriores) => ({
      ...anteriores,
      [campo]: undefined,
      ...(erroRelacionado && { [erroRelacionado]: undefined }),
    }))
    onAlterar()
  }

  function enviar(evento) {
    evento.preventDefault()
    if (buscando) return
    const resultado = validarPerfil({ nome, cnaes, porte, municipio, pesos })
    setErros(resultado.erros ?? {})

    if (resultado.erros) {
      const primeiroCampo = Object.keys(resultado.erros)[0]
      const campoFoco = primeiroCampo === 'totalPesos' ? 'peso_cnae' : primeiroCampo
      evento.currentTarget.elements.namedItem(campoFoco)?.focus()
      return
    }

    onBuscar(resultado.perfilValidado)
  }

  return (
    <form noValidate onSubmit={enviar} className="mt-6 space-y-7 rounded-2xl border border-divisor bg-superficie p-5 shadow-xs sm:p-8">
      <div>
        <label htmlFor="nome" className="mb-2 block text-sm font-semibold">Nome do perfil</label>
        <input
          {...atributosCampo('nome')}
          name="nome"
          required
          value={nome}
          onChange={(evento) => {
            setNome(evento.target.value)
            associacao?.mudarNome()
            limparValidacao('nome')
          }}
          onBlur={() => {
            if (associacao?.consulta.etapa === 'inicial') associacao.consultar(nome)
          }}
          className={estiloCampo}
        />
        <ErroCampo campo="nome" mensagem={erros.nome} />
      </div>

      {associacao && <ProdutoDoPerfil associacao={associacao} nome={nome} buscando={buscando} />}

      <fieldset className="min-w-0 space-y-3">
        <legend className="mb-2 font-semibold text-marinho">CNAEs desejados</legend>
        <PesquisaCnae
          atributos={atributosCampo('cnae', 'cnae-ajuda')}
          estiloCampo={estiloCampo}
          selecionados={cnaes}
          onAlterar={(codigos) => {
            setCnaes(codigos)
            limparValidacao('cnae')
          }}
        />
        <ErroCampo campo="cnae" mensagem={erros.cnae} />
      </fieldset>

      <div className="grid gap-5 border-y border-divisor py-6 sm:grid-cols-2">
        <div>
          <label htmlFor="porte" className="mb-2 block text-sm font-semibold">Porte empresarial</label>
          <select
            {...atributosCampo('porte')}
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
            {portesPerfil.map(({ codigo, rotulo }) => (
              <option key={codigo} value={codigo}>{rotulo}</option>
            ))}
          </select>
          <ErroCampo campo="porte" mensagem={erros.porte} />
        </div>

        <div>
          <PesquisaMunicipio
            atributos={atributosCampo('municipio', 'municipio-ajuda')}
            codigo={municipio}
            estiloCampo={estiloCampo}
            onAlterar={(codigo) => {
              setMunicipio(codigo)
              limparValidacao('municipio')
            }}
          />
          <ErroCampo campo="municipio" mensagem={erros.municipio} />
        </div>
      </div>

      <fieldset className="min-w-0 space-y-3">
        <legend className="mb-2 font-semibold text-marinho">Pesos dos critérios</legend>
        <div className="grid gap-4 sm:grid-cols-3">
          {criterios.map(({ chave, rotulo }) => (
            <div key={chave}>
              <label htmlFor={chave} className="mb-2 block text-sm font-medium">{rotulo}</label>
              <input
                {...atributosCampo(chave, erros.totalPesos && 'totalPesos-erro')}
                name={chave}
                type="number"
                min="0"
                max="100"
                step="1"
                required
                value={pesos[chave]}
                onChange={(evento) => {
                  setPesos({ ...pesos, [chave]: evento.target.value })
                  limparValidacao(chave, 'totalPesos')
                }}
                className={estiloCampo}
              />
              <ErroCampo campo={chave} mensagem={erros[chave]} />
            </div>
          ))}
        </div>
        <output htmlFor={criterios.map(({ chave }) => chave).join(' ')} className="block rounded-lg bg-fundo px-4 py-2.5 text-sm font-semibold text-texto">
          Total dos pesos: {total === null ? 'indisponível' : formatoTotal.format(total)}
        </output>
        <ErroCampo campo="totalPesos" mensagem={erros.totalPesos} />
      </fieldset>

      <button
        type="submit"
        disabled={buscando}
        className={`${estiloBotao} min-h-11 w-full bg-turquesa text-marinho hover:bg-turquesa/80 disabled:cursor-wait disabled:bg-acao-suave disabled:text-acao sm:w-auto`}
      >
        Buscar empresas
      </button>
    </form>
  )
}

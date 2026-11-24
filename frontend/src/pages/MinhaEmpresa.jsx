import { useEffect, useState } from 'react'
import { consultarEmpresa, salvarEmpresa } from '../services/empresaUsuariaHttp.js'
import { empresaVazia, validarEmpresa } from '../utils/empresaUsuaria.js'

const campos = [
  { chave: 'nome', rotulo: 'Nome da empresa', autoComplete: 'organization', maxLength: 200 },
  { chave: 'cnpj', rotulo: 'CNPJ', inputMode: 'numeric' },
  { chave: 'email', rotulo: 'E-mail', type: 'email', autoComplete: 'email', maxLength: 254 },
]

function CadastroEmpresa() {
  const [dados, setDados] = useState(empresaVazia)
  const [consulta, setConsulta] = useState({ etapa: 'carregando' })
  const [tentativa, setTentativa] = useState(0)
  const [erros, setErros] = useState({})
  const [envio, setEnvio] = useState({ etapa: 'inicial' })

  useEffect(() => {
    const controle = new AbortController()
    consultarEmpresa(controle.signal).then((empresa) => {
      if (controle.signal.aborted) return
      setDados(empresa ?? empresaVazia)
      setConsulta({ etapa: empresa ? 'cadastrada' : 'vazia' })
    }).catch((erro) => {
      if (!controle.signal.aborted) setConsulta({ etapa: 'erro', mensagem: erro.message })
    })
    return () => controle.abort()
  }, [tentativa])

  async function enviar(evento) {
    evento.preventDefault()
    if (envio.etapa === 'salvando') return
    const validacao = validarEmpresa(dados)
    setErros(validacao.erros)
    const primeiroCampo = Object.keys(validacao.erros)[0]
    if (primeiroCampo) {
      setEnvio({ etapa: 'inicial' })
      evento.currentTarget.elements.namedItem(primeiroCampo)?.focus()
      return
    }

    setEnvio({ etapa: 'salvando' })
    try {
      const empresa = await salvarEmpresa(validacao.dados)
      setDados(empresa)
      setConsulta({ etapa: 'cadastrada' })
      setEnvio({ etapa: 'sucesso' })
    } catch (erro) {
      setEnvio({ etapa: 'erro', mensagem: erro.message })
    }
  }

  if (consulta.etapa === 'carregando') {
    return <p role="status" className="mt-6 text-suave">Consultando empresa usuária…</p>
  }
  if (consulta.etapa === 'erro') {
    return (
      <div className="mt-6 rounded-xl border border-divisor bg-superficie p-5">
        <p role="alert" className="text-erro">Falha na consulta. {consulta.mensagem}</p>
        <button type="button" onClick={() => {
          setConsulta({ etapa: 'carregando' })
          setTentativa((atual) => atual + 1)
        }} className="mt-3 min-h-11 rounded-lg bg-turquesa px-4 font-semibold text-marinho">
          Tentar novamente
        </button>
      </div>
    )
  }

  const salvando = envio.etapa === 'salvando'
  return (
    <form noValidate onSubmit={enviar} className="mt-6 max-w-2xl space-y-4 rounded-2xl border border-divisor bg-superficie p-5 sm:p-8">
      {consulta.etapa === 'vazia' && <p className="text-suave">Nenhuma empresa cadastrada. Preencha os dados para criar o cadastro.</p>}
      <fieldset disabled={salvando} className="min-w-0 space-y-4">
        <legend className="font-semibold text-marinho">Dados da empresa</legend>
        {campos.map(({ chave, rotulo, ...atributos }) => (
          <div key={chave}>
            <label htmlFor={`empresa-${chave}`} className="mb-2 block text-sm font-semibold">{rotulo}</label>
            <input
              {...atributos}
              id={`empresa-${chave}`}
              name={chave}
              required
              value={dados[chave]}
              aria-invalid={Boolean(erros[chave])}
              aria-describedby={erros[chave] ? `erro-empresa-${chave}` : undefined}
              onChange={(evento) => {
                setDados({ ...dados, [chave]: evento.target.value })
                setErros({ ...erros, [chave]: undefined })
                setEnvio({ etapa: 'inicial' })
              }}
              className="w-full rounded-lg border border-controle bg-superficie px-3 py-2.5 aria-invalid:border-erro"
            />
            {erros[chave] && <p id={`erro-empresa-${chave}`} className="mt-2 text-sm text-erro">{erros[chave]}</p>}
          </div>
        ))}
        <button type="submit" className="min-h-11 w-full rounded-lg bg-turquesa px-4 text-sm font-semibold text-marinho disabled:opacity-60 sm:w-auto">
          Salvar empresa
        </button>
      </fieldset>
      <div role="status" className="text-sm text-acao">
        {salvando && 'Salvando empresa…'}
        {envio.etapa === 'sucesso' && 'Dados da empresa salvos com sucesso.'}
      </div>
      {envio.etapa === 'erro' && <p role="alert" className="text-sm text-erro">{envio.mensagem}</p>}
    </form>
  )
}

export default function MinhaEmpresa() {
  const modo = import.meta.env.VITE_RADARLEAD_MODO || 'simulado'
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 sm:py-12">
      <h1 className="text-3xl font-bold tracking-tight text-marinho sm:text-4xl">Minha empresa</h1>
      <p className="mt-3 text-sm text-suave">Modo demonstração — sem autenticação de usuários</p>
      {modo === 'http' ? <CadastroEmpresa /> : (
        <p className="mt-6 rounded-xl border border-divisor bg-superficie p-5 text-suave">
          O cadastro real exige a API do RadarLead. Ative o modo HTTP para consultar e salvar os dados da empresa.
        </p>
      )}
    </main>
  )
}

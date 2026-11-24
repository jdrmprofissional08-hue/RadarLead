import { useEffect, useRef, useState } from 'react'
import { cadastrarProduto, listarProdutos } from '../services/produtosHttp.js'

const campo = 'w-full rounded-lg border border-controle bg-superficie px-3 py-2.5 aria-invalid:border-erro'
const botao = 'min-h-11 rounded-lg bg-turquesa px-4 text-sm font-semibold text-marinho disabled:opacity-60'

function CatalogoProdutos() {
  const [consulta, setConsulta] = useState({ etapa: 'carregando' })
  const [tentativa, setTentativa] = useState(0)
  const [nome, setNome] = useState('')
  const [descricao, setDescricao] = useState('')
  const [erroNome, setErroNome] = useState('')
  const [envio, setEnvio] = useState({ etapa: 'inicial' })
  const emEnvio = useRef(false)

  useEffect(() => {
    const controle = new AbortController()
    listarProdutos(controle.signal).then((produtos) => {
      if (!controle.signal.aborted) setConsulta({ etapa: 'pronta', produtos })
    }).catch((erro) => {
      if (!controle.signal.aborted) setConsulta({ etapa: 'erro', mensagem: erro.message })
    })
    return () => controle.abort()
  }, [tentativa])

  async function enviar(evento) {
    evento.preventDefault()
    if (emEnvio.current) return
    const nomeLimpo = nome.trim()
    if (!nomeLimpo || nomeLimpo.length > 200) {
      setErroNome('Informe um nome de até 200 caracteres.')
      setEnvio({ etapa: 'inicial' })
      evento.currentTarget.elements.namedItem('nome')?.focus()
      return
    }

    emEnvio.current = true
    setEnvio({ etapa: 'salvando' })
    try {
      const produto = await cadastrarProduto({ nome: nomeLimpo, descricao: descricao.trim() })
      setConsulta((atual) => ({
        etapa: 'pronta',
        produtos: [...atual.produtos.filter(({ id }) => id !== produto.id), produto],
      }))
      setNome('')
      setDescricao('')
      setEnvio({ etapa: 'sucesso' })
    } catch (erro) {
      setEnvio({ etapa: 'erro', mensagem: erro.message })
    } finally {
      emEnvio.current = false
    }
  }

  if (consulta.etapa === 'carregando') return <p role="status" className="mt-3 text-suave">Consultando produtos e serviços…</p>
  if (consulta.etapa === 'erro') return (
    <>
      <p role="alert" className="mt-3 text-erro">Falha na consulta de produtos. {consulta.mensagem}</p>
      <button type="button" className={`mt-3 ${botao}`} onClick={() => {
        setConsulta({ etapa: 'carregando' })
        setTentativa((atual) => atual + 1)
      }}>Tentar consultar produtos novamente</button>
    </>
  )

  const salvando = envio.etapa === 'salvando'
  return (
    <>
      {consulta.produtos.length === 0 ? (
        <p className="mt-3 text-suave">Nenhum produto ou serviço cadastrado.</p>
      ) : (
        <ul aria-label="Produtos e serviços cadastrados" className="mt-3 divide-y divide-divisor">
          {consulta.produtos.map((produto) => (
            <li key={produto.id} className="py-3 wrap-break-word">
              <h3 className="font-semibold text-marinho">{produto.nome}</h3>
              <p className="whitespace-pre-wrap text-sm text-suave">{produto.descricao || 'Sem descrição.'}</p>
            </li>
          ))}
        </ul>
      )}
      <form noValidate onSubmit={enviar} className="mt-5 border-t border-divisor pt-5">
        <fieldset disabled={salvando} className="min-w-0 space-y-3">
          <legend className="font-semibold text-marinho">Cadastrar produto ou serviço</legend>
          <div>
            <label htmlFor="produto-nome" className="mb-2 block text-sm font-semibold">Nome do produto ou serviço</label>
            <input id="produto-nome" name="nome" required maxLength={200} value={nome}
              aria-invalid={Boolean(erroNome)} aria-describedby={erroNome ? 'produto-nome-erro' : undefined}
              onChange={(evento) => {
                setNome(evento.target.value)
                setErroNome('')
                setEnvio({ etapa: 'inicial' })
              }} className={campo} />
            {erroNome && <p id="produto-nome-erro" className="mt-2 text-sm text-erro">{erroNome}</p>}
          </div>
          <div>
            <label htmlFor="produto-descricao" className="mb-2 block text-sm font-semibold">Descrição (opcional)</label>
            <textarea id="produto-descricao" rows={3} value={descricao} onChange={(evento) => {
              setDescricao(evento.target.value)
              setEnvio({ etapa: 'inicial' })
            }} className={campo} />
          </div>
          <button type="submit" className={`w-full sm:w-auto ${botao}`}>Salvar produto ou serviço</button>
        </fieldset>
        <div role="status" className="mt-3 text-sm text-acao">
          {salvando && 'Salvando produto ou serviço…'}
          {envio.etapa === 'sucesso' && 'Produto ou serviço cadastrado com sucesso.'}
        </div>
        {envio.etapa === 'erro' && <p role="alert" className="mt-3 text-sm text-erro">{envio.mensagem}</p>}
      </form>
    </>
  )
}

const orientacoes = {
  vazia: 'Cadastre primeiro a empresa para consultar e cadastrar produtos ou serviços.',
  erro: 'Produtos e serviços estarão disponíveis após confirmar o cadastro da empresa.',
  simulado: 'A consulta e o cadastro de produtos e serviços exigem a API do RadarLead.',
}

export default function ProdutosEmpresa({ estadoEmpresa, empresaId }) {
  return (
    <section aria-labelledby="titulo-produtos" className="mt-6 max-w-2xl rounded-2xl border border-divisor bg-superficie p-5 sm:p-8">
      <h2 id="titulo-produtos" className="text-xl font-semibold text-marinho">Produtos e serviços</h2>
      {estadoEmpresa === 'cadastrada' ? <CatalogoProdutos key={empresaId} /> : (
        <p className="mt-3 text-suave">{orientacoes[estadoEmpresa]}</p>
      )}
    </section>
  )
}

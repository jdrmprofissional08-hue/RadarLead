import { Link } from 'react-router'

export default function ProdutoDoPerfil({ associacao, nome, buscando }) {
  const {
    consulta, consultar, perfil, produtos, podeEditar, intencao, escolher, aviso,
  } = associacao
  const vinculado = produtos.find(({ id }) => id === perfil?.produto_id)

  return (
    <fieldset className="min-w-0 space-y-3 rounded-lg border border-divisor p-4">
      <legend className="px-1 font-semibold text-marinho">Produto ou serviço associado</legend>
      {consulta.etapa === 'inicial' && (
        <p className="text-sm text-suave">Informe o nome do perfil para consultar o vínculo.</p>
      )}
      {consulta.etapa === 'carregando' && <p role="status">Consultando o vínculo e os produtos…</p>}
      {consulta.etapa === 'erro' && (
        <>
          <p role="alert" className="text-sm text-erro">{consulta.mensagem}</p>
          <button type="button" className="min-h-11 font-semibold text-acao" onClick={() => consultar(nome)}>
            Tentar consultar vínculo novamente
          </button>
        </>
      )}
      {['pronta', 'ambigua', 'semEmpresa'].includes(consulta.etapa) && (
        <button type="button" disabled={buscando} className="min-h-11 font-semibold text-acao" onClick={() => consultar(nome)}>
          Atualizar consulta do vínculo
        </button>
      )}
      {consulta.etapa === 'ambigua' && <p>Há mais de um perfil correspondente. A alteração do vínculo está indisponível.</p>}
      {consulta.etapa === 'semEmpresa' && <p>Cadastre a empresa em <Link className="text-acao underline" to="/minha-empresa">Minha empresa</Link> para associar produtos.</p>}
      {perfil ? (
        <p className="break-words">
          {perfil.produto_id === null ? 'Perfil geral, sem produto associado.' :
            vinculado ? `Vínculo atual: ${vinculado.nome}` : 'Os dados do produto associado estão indisponíveis.'}
        </p>
      ) : podeEditar && <p>Nenhum perfil correspondente foi encontrado na consulta.</p>}
      {podeEditar && produtos.length === 0 && (
        <p>Cadastre um produto ou serviço em <Link className="text-acao underline" to="/minha-empresa">Minha empresa</Link>.</p>
      )}
      {podeEditar && produtos.length > 0 && (
        <div>
          <label htmlFor="produto-perfil" className="mb-2 block text-sm font-semibold">Escolher produto ou serviço</label>
          <select id="produto-perfil" disabled={buscando}
            value={intencao.tipo === 'associar' ? String(intencao.id) : ''}
            onChange={(evento) => escolher(evento.target.value
              ? { tipo: 'associar', id: Number(evento.target.value) } : { tipo: 'manter' })}
            className="w-full min-w-0 rounded-lg border border-controle bg-superficie px-3 py-2.5"
          >
            <option value="">Manter vínculo como está</option>
            {produtos.map(({ id, nome: rotulo }) => <option key={id} value={id}>{rotulo}</option>)}
          </select>
        </div>
      )}
      {podeEditar && perfil?.produto_id != null && intencao.tipo !== 'remover' && (
        <button type="button" disabled={buscando} className="min-h-11 font-semibold text-acao"
          onClick={() => escolher({ tipo: 'remover' })}>Remover associação</button>
      )}
      {intencao.tipo !== 'manter' && (
        <div className="flex flex-wrap items-center gap-x-4 text-sm">
          <p>{intencao.tipo === 'remover' ? 'Remoção pendente.' : 'Associação pendente.'}</p>
          <button type="button" disabled={buscando} className="min-h-11 font-semibold text-acao"
            onClick={() => escolher({ tipo: 'manter' })}>Cancelar alteração</button>
        </div>
      )}
      {aviso && <p role={aviso.erro ? 'alert' : 'status'} className={aviso.erro ? 'text-erro' : 'text-acao'}>{aviso.texto}</p>}
    </fieldset>
  )
}

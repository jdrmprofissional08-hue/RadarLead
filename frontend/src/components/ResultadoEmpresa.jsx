import { municipiosProvisorios } from '../utils/perfilProspeccao.js'

const formatoPontos = new Intl.NumberFormat('pt-BR', { maximumSignificantDigits: 21 })
const indisponivel = 'Não informado'
const rotulosPorte = new Map([[1, 'ME'], [3, 'EPP'], [5, 'Demais']])

export default function ResultadoEmpresa({ empresa }) {
  const municipio = municipiosProvisorios.find(
    ({ codigo }) => codigo === empresa.municipio_ibge,
  )
  const cnae = empresa.cnae_principal?.replace(/^(\d{4})(\d)(\d{2})$/, '$1-$2/$3')
  const pontuacao = Number.isFinite(empresa.pontuacao)
    ? `${formatoPontos.format(empresa.pontuacao)} ${empresa.pontuacao === 1 ? 'ponto' : 'pontos'}`
    : indisponivel

  return (
    <article className="rounded-lg border border-slate-800 bg-slate-900 p-5 sm:p-6">
      <header className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <h2 className="min-w-0 text-xl font-semibold wrap-break-word">
          {empresa.razao_social || 'Empresa sem nome informado'}
        </h2>
        <p className="max-w-full text-sm font-semibold wrap-break-word text-emerald-300">
          Pontuação: {pontuacao}
        </p>
      </header>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-slate-400">CNAE principal</dt>
          <dd>{cnae || indisponivel}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Porte</dt>
          <dd>{rotulosPorte.get(empresa.porte) ?? indisponivel}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Município</dt>
          <dd>{municipio ? `${municipio.nome} (${municipio.uf})` : empresa.municipio_ibge || indisponivel}</dd>
        </div>
      </dl>

      <h3 className="mt-5 text-sm font-semibold">Justificativas</h3>
      {empresa.justificativas?.length > 0 ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">
          {empresa.justificativas.map((justificativa, indice) => (
            <li key={indice}>{justificativa}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-slate-300">Nenhuma justificativa informada</p>
      )}
    </article>
  )
}

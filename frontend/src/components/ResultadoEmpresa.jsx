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
    <article className="rounded-xl border border-divisor bg-superficie p-4 shadow-xs sm:p-5">
      <header className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1.5">
        <h2 className="min-w-0 text-xl font-semibold wrap-break-word text-marinho">
          {empresa.razao_social || 'Empresa sem nome informado'}
        </h2>
        <p className="max-w-full rounded-md bg-acao-suave px-3 py-1.5 text-sm font-semibold wrap-break-word text-acao">
          Pontuação: {pontuacao}
        </p>
      </header>

      <dl className="mt-3 grid gap-2 rounded-lg bg-fundo px-3 py-2.5 text-sm sm:grid-cols-3">
        <div>
          <dt className="mb-0.5 font-medium text-suave">CNAE principal</dt>
          <dd>{cnae || indisponivel}</dd>
        </div>
        <div>
          <dt className="mb-0.5 font-medium text-suave">Porte</dt>
          <dd>{rotulosPorte.get(empresa.porte) ?? indisponivel}</dd>
        </div>
        <div>
          <dt className="mb-0.5 font-medium text-suave">Município</dt>
          <dd>{municipio ? `${municipio.nome} (${municipio.uf})` : empresa.municipio_ibge || indisponivel}</dd>
        </div>
      </dl>

      <h3 className="mt-3 text-sm font-semibold">Justificativas</h3>
      {empresa.justificativas?.length > 0 ? (
        <ul className="mt-1 list-disc pl-5 text-sm leading-5 text-suave">
          {empresa.justificativas.map((justificativa, indice) => (
            <li key={indice}>{justificativa}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-sm text-suave">Nenhuma justificativa informada</p>
      )}
    </article>
  )
}

import CampoPesquisa from './CampoPesquisa.jsx'
import { cnaesPorCodigo, formatarCnae, pesquisarCnaes } from '../utils/pesquisaCnae.js'

export default function PesquisaCnae({ selecionados, onAlterar, atributos, estiloCampo }) {
  return (
    <CampoPesquisa
      atributos={atributos}
      estiloCampo={estiloCampo}
      rotulo="Pesquisar por atividade ou código CNAE"
      ajuda="Selecione pelo menos uma atividade. Use as setas e Enter para selecionar ou Escape para fechar."
      rotuloLista="Sugestões de CNAE"
      semResultados="Nenhuma atividade encontrada."
      pesquisar={pesquisarCnaes}
      renderizarOpcao={({ codigo, descricao }) => <><strong>{formatarCnae(codigo)}</strong><span>{descricao}</span></>}
      desabilitada={(codigo) => selecionados.includes(codigo)}
      onSelecionar={(codigo) => onAlterar([...selecionados, codigo])}
    >
      {selecionados.length > 0 && (
        <ul aria-label="CNAEs adicionados" className="mt-3 flex flex-wrap gap-2">
          {selecionados.map((codigo) => (
            <li key={codigo} className="max-w-full">
              <button
                type="button"
                aria-label={`Remover CNAE ${codigo}, ${cnaesPorCodigo.get(codigo).descricao}`}
                onClick={() => {
                  document.getElementById(atributos.id)?.focus()
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
    </CampoPesquisa>
  )
}

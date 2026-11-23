import { buscarEmpresasHttp, ErroProspeccaoHttp } from './prospeccaoHttp.js'
import { buscarEmpresasSimuladas } from './prospeccaoSimulada.js'

export function obterServicoProspeccao() {
  const modo = import.meta.env.VITE_RADARLEAD_MODO || 'simulado'

  if (modo === 'simulado') return { modo, buscarEmpresas: buscarEmpresasSimuladas }
  if (modo === 'http') return { modo, buscarEmpresas: buscarEmpresasHttp }

  return {
    modo,
    async buscarEmpresas() {
      throw new ErroProspeccaoHttp('Modo de prospecção inválido. Configure VITE_RADARLEAD_MODO como simulado ou http.')
    },
  }
}

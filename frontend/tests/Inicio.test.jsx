// @vitest-environment jsdom
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, expect, it, vi } from 'vitest'
import Inicio from '../src/pages/Inicio.jsx'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

it.each(['http', 'simulado'])('orienta a primeira visita no modo %s sem consultar a API', (modo) => {
  vi.stubEnv('VITE_RADARLEAD_MODO', modo)
  const consultar = vi.fn()
  vi.stubGlobal('fetch', consultar)
  render(<MemoryRouter><Inicio /></MemoryRouter>)

  const inicio = within(screen.getByRole('main'))
  expect(inicio.getByRole('link', { name: 'Abrir perfil de prospecção' })).toHaveAttribute('href', '/perfil')
  if (modo === 'http') {
    expect(inicio.getByText(/quem está prospectando e, se quiser, os produtos e serviços/)).toHaveTextContent(
      /perfil de cliente ideal.*empresas que deseja encontrar.*execute a prospecção/,
    )
    expect(inicio.getByRole('link', { name: 'Minha empresa' })).toHaveAttribute('href', '/minha-empresa')
  } else {
    expect(inicio.getByText(/prospecção com dados simulados/)).toBeInTheDocument()
    expect(inicio.queryByRole('link', { name: 'Minha empresa' })).not.toBeInTheDocument()
  }
  expect(consultar).not.toHaveBeenCalled()
})

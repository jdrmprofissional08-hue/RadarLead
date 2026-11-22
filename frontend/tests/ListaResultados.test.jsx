// @vitest-environment jsdom
import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import ListaResultados from '../src/components/ListaResultados.jsx'

it('ordena por pontos, mantém empates e exibe zero e os três portes', () => {
  const resultados = Object.freeze([
    { id: 'a', razao_social: 'Alfa', pontuacao: 0, porte: 1 },
    { id: 'b', razao_social: 'Beta', pontuacao: 50, porte: 3 },
    { id: 'c', razao_social: 'Gama', pontuacao: 100, porte: 5, justificativas: ['CNAE compatível'] },
    { id: 'd', razao_social: 'Delta', pontuacao: 50, porte: 5 },
  ])

  render(<ListaResultados resultados={resultados} />)
  const cartoes = screen.getAllByRole('article')
  expect(cartoes.map((cartao) => within(cartao).getByRole('heading', { level: 2 }).textContent))
    .toEqual(['Gama', 'Beta', 'Delta', 'Alfa'])
  expect(within(cartoes[0]).getByText('Demais')).toBeInTheDocument()
  expect(within(cartoes[0]).getByText('CNAE compatível')).toBeInTheDocument()
  expect(within(cartoes[1]).getByText('EPP')).toBeInTheDocument()
  expect(within(cartoes[3]).getByText('ME')).toBeInTheDocument()
  expect(within(cartoes[3]).getByText('Pontuação: 0 pontos')).toBeInTheDocument()
})

it('exibe o estado vazio', () => {
  render(<ListaResultados resultados={[]} />)
  expect(screen.getByText('Nenhuma empresa encontrada')).toBeInTheDocument()
  expect(screen.queryByRole('article')).not.toBeInTheDocument()
})

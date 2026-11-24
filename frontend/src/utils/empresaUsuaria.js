export const empresaVazia = { nome: '', cnpj: '', email: '' }

function cnpjValido(cnpj) {
  if (!/^\d{14}$/.test(cnpj) || /^(\d)\1+$/.test(cnpj)) return false

  function digito(tamanho) {
    let peso = tamanho - 7
    let soma = 0
    for (const numero of cnpj.slice(0, tamanho)) {
      soma += Number(numero) * peso
      peso = peso === 2 ? 9 : peso - 1
    }
    return (soma * 10) % 11 % 10
  }

  return digito(12) === Number(cnpj[12]) && digito(13) === Number(cnpj[13])
}

export function validarEmpresa({ nome, cnpj, email }) {
  const dados = {
    nome: nome.trim(),
    cnpj: cnpj.trim().replace(/[./-]/g, ''),
    email: email.trim(),
  }
  const erros = {}
  if (!dados.nome || dados.nome.length > 200) erros.nome = 'Informe um nome de até 200 caracteres.'
  if (!cnpjValido(dados.cnpj)) erros.cnpj = 'Informe um CNPJ com dígitos verificadores válidos.'
  if (dados.email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(dados.email)) {
    erros.email = 'Informe um e-mail válido.'
  }
  return { dados, erros }
}

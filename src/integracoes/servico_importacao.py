
from importlib import import_module


def obter_erros_backend():
    """Carrega as excecoes do backend quando disponivel."""
    try:
        modulo = import_module("src.excecoes")
    except ModuleNotFoundError as erro:
        if erro.name != "src.excecoes":
            raise
        return (), ()

    return (
        (modulo.DadosInvalidosError,),
        (modulo.EmpresaNaoEncontradaError,)
    )


class ServicoImportacaoEmpresas:
    """Importa empresas consultadas para um repositorio."""

    def __init__(
        self,
        consulta,
        repositorio,
        erros_dominio=None,
        erros_empresa_nao_encontrada=None
    ):
        self.consulta = consulta
        self.repositorio = repositorio

        padrao_dominio, padrao_nao_encontrada = (
            obter_erros_backend()
        )

        if erros_dominio is None:
            erros_dominio = padrao_dominio

        if erros_empresa_nao_encontrada is None:
            erros_empresa_nao_encontrada = padrao_nao_encontrada

        self.erros_dominio = tuple(erros_dominio)
        self.erros_empresa_nao_encontrada = tuple(
            erros_empresa_nao_encontrada
        )

    def importar_cnpjs(self, cnpjs, classe_empresa=None):
        if not isinstance(cnpjs, list):
            raise ValueError("Os CNPJs devem estar em uma lista")

        resultado = {
            "importados": [],
            "duplicados": [],
            "ja_cadastrados": [],
            "falhas": []
        }

        vistos = set()

        erros_recuperaveis = (
            ValueError,
            ConnectionError
        ) + self.erros_dominio

        for original in cnpjs:
            if not isinstance(original, str):
                resultado["falhas"].append({
                    "cnpj": str(original),
                    "erro": "CNPJ deve ser texto"
                })
                continue

            cnpj = original.strip()
            cnpj = cnpj.replace(".", "").replace("/", "")
            cnpj = cnpj.replace("-", "")

            if (
                len(cnpj) != 14
                or not cnpj.isascii()
                or not cnpj.isdigit()
            ):
                resultado["falhas"].append({
                    "cnpj": original,
                    "erro": "CNPJ invalido"
                })
                continue

            # Verifica repeticoes no lote recebido.
            if cnpj in vistos:
                resultado["duplicados"].append(cnpj)
                continue

            vistos.add(cnpj)

            # Consulta apenas o CNPJ atual no repositorio.
            try:
                self.repositorio.buscar_empresa(cnpj)

            except self.erros_empresa_nao_encontrada:
                # Empresa nao existe: podemos importar.
                pass

            else:
                # Empresa encontrada: nao consulta a API.
                resultado["ja_cadastrados"].append(cnpj)
                continue

            # Consulta e converte a empresa.
            try:
                empresa = self.consulta.consultar_empresa(
                    cnpj,
                    classe_empresa=classe_empresa
                )

            except erros_recuperaveis as erro:
                resultado["falhas"].append({
                    "cnpj": cnpj,
                    "erro": str(erro)
                })
                continue

            # Salva a nova empresa no repositorio.
            self.repositorio.salvar_empresa(empresa)

            resultado["importados"].append(cnpj)

        return resultado


from importlib import import_module


def obter_erros_dominio():
    """Carrega as excecoes do backend quando disponivel."""
    try:
        modulo = import_module("src.excecoes")
    except ModuleNotFoundError as erro:
        if erro.name != "src.excecoes":
            raise
        return ()

    return (modulo.DadosInvalidosError,)


class ServicoImportacaoEmpresas:
    """Importa empresas consultadas para um repositorio."""

    def __init__(self, consulta, repositorio, erros_dominio=None):
        self.consulta = consulta
        self.repositorio = repositorio

        if erros_dominio is None:
            erros_dominio = obter_erros_dominio()

        self.erros_dominio = tuple(erros_dominio)

    def importar_cnpjs(self, cnpjs, classe_empresa=None):
        if not isinstance(cnpjs, list):
            raise ValueError("Os CNPJs devem estar em uma lista")

        resultado = {
            "importados": [],
            "duplicados": [],
            "ja_cadastrados": [],
            "falhas": []
        }

        existentes = {
            empresa.cnpj
            for empresa in self.repositorio.listar_empresas()
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

            if cnpj in vistos:
                resultado["duplicados"].append(cnpj)
                continue

            vistos.add(cnpj)

            if cnpj in existentes:
                resultado["ja_cadastrados"].append(cnpj)
                continue

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

            self.repositorio.salvar_empresa(empresa)
            existentes.add(cnpj)

            resultado["importados"].append(cnpj)

        return resultado


class ServicoImportacaoEmpresas:
    """Importa empresas consultadas para um repositorio."""

    def __init__(self, consulta, repositorio):
        self.consulta = consulta
        self.repositorio = repositorio

    def importar_cnpjs(self, cnpjs, classe_empresa=None):
        if not isinstance(cnpjs, list):
            raise ValueError("Os CNPJs devem estar em uma lista")

        resultado = {
            "importados": [],
            "duplicados": [],
            "ja_cadastrados": [],
            "falhas": []
        }

        # Consulta as empresas que ja estao no repositorio.
        existentes = {
            empresa.cnpj
            for empresa in self.repositorio.listar_empresas()
        }

        vistos = set()

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

            # Evita repeticoes dentro da lista recebida.
            if cnpj in vistos:
                resultado["duplicados"].append(cnpj)
                continue

            vistos.add(cnpj)

            # Evita consultar empresas ja cadastradas.
            if cnpj in existentes:
                resultado["ja_cadastrados"].append(cnpj)
                continue

            try:
                empresa = self.consulta.consultar_empresa(
                    cnpj,
                    classe_empresa=classe_empresa
                )

            except (ValueError, ConnectionError) as erro:
                resultado["falhas"].append({
                    "cnpj": cnpj,
                    "erro": str(erro)
                })
                continue

            # Persiste a empresa e atualiza o conjunto local.
            self.repositorio.salvar_empresa(empresa)
            existentes.add(cnpj)

            resultado["importados"].append(cnpj)

        return resultado


class ClassificadorPorConteudo:

    def __init__(self, peso_cnae=50, peso_porte=25, peso_localizacao=25):
        self.peso_cnae = peso_cnae
        self.peso_porte = peso_porte
        self.peso_localizacao = peso_localizacao

    def classificar(self, empresa, perfil):
        pontuacao = 0
        justificativas = []

        if empresa["cnae_principal"] in perfil["cnaes_desejados"]:
            pontuacao += self.peso_cnae
            justificativas.append(
                f"CNAE compatível: +{self.peso_cnae} pontos"
            )
        else:
            justificativas.append("CNAE diferente: +0 pontos")

        if empresa["porte"] == perfil["porte_desejado"]:
            pontuacao += self.peso_porte
            justificativas.append(
                f"Porte compatível: +{self.peso_porte} pontos"
            )
        else:
            justificativas.append("Porte diferente: +0 pontos")

        if empresa["municipio_ibge"] == perfil["municipio_alvo_ibge"]:
            pontuacao += self.peso_localizacao
            justificativas.append(
                f"Município compatível: +{self.peso_localizacao} pontos"
            )
        else:
            justificativas.append("Município diferente: +0 pontos")

        return {
            "pontuacao": pontuacao,
            "justificativas": justificativas
        }

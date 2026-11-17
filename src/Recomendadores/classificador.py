
class ClassificadorPorConteudo:
    def __init__(self, peso_cnae=50, peso_porte=25, peso_localizacao=25):
        self.peso_cnae = peso_cnae
        self.peso_porte = peso_porte
        self.peso_localizacao = peso_localizacao

    def classificar(self, empresa, perfil):
        pontuacao = 0

        if empresa["cnae_principal"] in perfil["cnaes_desejados"]:
            pontuacao += self.peso_cnae

        if empresa["porte"] == perfil["porte_desejado"]:
            pontuacao += self.peso_porte

        if empresa["municipio_ibge"] == perfil["municipio_alvo_ibge"]:
            pontuacao += self.peso_localizacao

        return pontuacao

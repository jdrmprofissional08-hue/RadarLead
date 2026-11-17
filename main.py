from src.Recomendadores.classificador import ClassificadorPorConteudo
import os

empresa = {
    "cnae_principal": "6204000",
    "porte": 5,
    "municipio_ibge": "5208707"
}

perfil = {
    "cnaes_desejados": ["6204000", "6201501"],
    "porte_desejado": 3,
    "municipio_alvo_ibge": "5208707"
}

classificador = ClassificadorPorConteudo()

resultado = classificador.classificar(empresa, perfil)

print("Pontuação da empresa:", resultado)

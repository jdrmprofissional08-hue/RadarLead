
from src.Recomendadores.classificador import ClassificadorPorConteudo

perfil = {
    "cnaes_desejados": ["6204000"],
    "porte_desejado": 3,
    "municipio_alvo_ibge": "5208707"
}

empresas = [
    {
        "cnpj": "11111111000111",
        "razao_social": "Restaurante A",
        "cnae_principal": "6204000",
        "porte": 3,
        "municipio_ibge": "5208707"
    },
    {
        "cnpj": "22222222000122",
        "razao_social": "Empresa B",
        "cnae_principal": "6204000",
        "porte": 5,
        "municipio_ibge": "5208707"
    }
]

classificador = ClassificadorPorConteudo()

print("\n--- RECOMENDAÇÕES ---")

recomendacoes = classificador.recomendar(empresas, perfil)

for item in recomendacoes:
    print(
        item["razao_social"],
        "-", item["pontuacao"], "pontos"
    )


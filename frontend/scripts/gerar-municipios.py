"""Converte a resposta da API de localidades do IBGE em JSON do frontend."""
import json
import re
import sys
from pathlib import Path

entrada = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
municipios = {}
for item in entrada:
    codigo = str(item["id"])
    nome = item["nome"].strip()
    imediata = item.get("regiao-imediata")
    micro = item.get("microrregiao")
    regioes = [
        regiao["UF"]
        for regiao in (
            imediata and imediata["regiao-intermediaria"],
            micro and micro["mesorregiao"],
        )
        if regiao
    ]
    ufs = {regiao["sigla"] for regiao in regioes if str(regiao["id"]) == codigo[:2]}
    if not re.fullmatch(r"[0-9]{7}", codigo) or not nome or codigo in municipios or len(ufs) != 1:
        raise ValueError(f"Registro inválido ou duplicado: {codigo}")
    uf, = ufs
    if not re.fullmatch(r"[A-Z]{2}", uf):
        raise ValueError(f"UF inválida: {uf}")
    municipios[codigo] = dict(codigo=codigo, nome=nome, uf=uf)

if not municipios:
    raise ValueError("A API não retornou municípios")

destino = Path(__file__).resolve().parents[1] / "src/data/municipios.json"
linhas = [json.dumps(municipios[codigo], ensure_ascii=False) for codigo in sorted(municipios)]
destino.write_text("[\n  " + ",\n  ".join(linhas) + "\n]\n", encoding="utf-8")

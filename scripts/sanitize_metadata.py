import sys
from pathlib import Path
sys.path.insert(0, r"H:\Meu Drive\DEV\analise-historica-incendios")
import geopandas as gpd
import pandas as pd
from src.config import GEOJSON_UCS, CSV_METADATA_UCS, DATA_PROCESSED

# Carregar shapes oficiais diretamente do GeoJSON
gdf = gpd.read_file(GEOJSON_UCS)

# Dicionario oficial de nomes limpos com acentuacao grafica correta UTF-8
nomes_limpos = {
    1: "Área de Proteção Ambiental da Ilha de Combu",
    2: "Área de Proteção Ambiental da Região Metropolitana de Belém",
    3: "Área de Proteção Ambiental de Algodoal-Maiandeua",
    4: "Área de Proteção Ambiental de São Geraldo do Araguaia",
    5: "Área de Proteção Ambiental do Lago de Tucuruí",
    6: "Área de Proteção Ambiental do Marajó",
    7: "Área de Proteção Ambiental Paytuna",
    8: "Área de Proteção Ambiental Triunfo do Xingu",
    9: "Estação Ecológica do Grão-Pará",
    10: "Estação Ecológica Mamuru",
    11: "Floresta Estadual do Iriri",
    12: "Floresta Estadual do Paru",
    13: "Floresta Estadual do Trombetas",
    14: "Floresta Estadual de Faro",
    15: "Monumento Natural Atalaia",
    16: "Parque Estadual Ambiental das Árvores Gigantes da Amazônia",
    17: "Parque Estadual Charapucu",
    18: "Parque Estadual da Serra dos Martírios/Andorinhas",
    19: "Parque Estadual do Utinga 'Camillo Vianna'",
    20: "Parque Estadual Monte Alegre - PEMA",
    21: "Refúgio de Vida Silvestre Metrópole da Amazônia",
    22: "Refúgio de Vida Silvestre Padre Sérgio Tonetto",
    23: "Refúgio de Vida Silvestre Rios São Benedito e Azul",
    24: "Refúgio de Vida Silvestre Tabuleiro do Embaubal",
    25: "Reserva Biológica do Maicuru",
    26: "Reserva de Desenvolvimento Sustentável Alcobaça",
    27: "Reserva de Desenvolvimento Sustentável Campo das Mangabas",
    28: "Reserva de Desenvolvimento Sustentável Pucuruí-Ararão",
    29: "Reserva de Desenvolvimento Sustentável Vitória de Souzel"
}

rows = []
for _, r in gdf.sort_values("id").iterrows():
    uid = int(r["id"])
    nome_correto = nomes_limpos.get(uid, r.get("nome_", f"UC {uid}"))
    gerencia = str(r.get("gerencia", "")).strip()
    grupo = str(r.get("grupo", "")).strip()
    cat = str(r.get("categoria", "")).strip()
    mun = str(r.get("municipio_", "")).strip()
    dt_cria = str(r.get("data_de_cr", "")).strip()
    
    # Ano de criacao
    ano_cria = None
    if dt_cria and "/" in dt_cria:
        try:
            ano_cria = int(dt_cria.split("/")[-1])
        except Exception:
            pass
    if not ano_cria and "criacao" in r and pd.notna(r["criacao"]):
        try:
            ano_cria = int(str(r["criacao"])[:4])
        except Exception:
            pass

    area_ha = float(r.get("area_ha", 0.0))
    area_km2 = round(area_ha / 100.0, 2)

    rows.append({
        "id": uid,
        "nome": nome_correto,
        "categoria": cat,
        "grupo": grupo,
        "gerencia": gerencia,
        "municipio": mun,
        "data_criacao": dt_cria,
        "ano_criacao": ano_cria,
        "area_ha": round(area_ha, 2),
        "area_km2": area_km2,
        "tipo_floresta": "Floresta Tropical Úmida / Transição",
        "situacao_legal": "Decretada / Regularizada"
    })

df_clean = pd.DataFrame(rows)
df_clean.to_csv(CSV_METADATA_UCS, index=False, encoding="utf-8")
print(f"Metadados sanitizados com 9 Gerências Oficiais salvos em: {CSV_METADATA_UCS}")

# Atualizar tambem o CSV de series historicas mapbiomas_fogo_series_1985_2023.csv
csv_series = DATA_PROCESSED / "mapbiomas_fogo_series_1985_2023.csv"
if csv_series.exists():
    df_series = pd.read_csv(csv_series)
    # Criar mapa id -> gerencia e id -> nome
    ger_map = dict(zip(df_clean["id"], df_clean["gerencia"]))
    nome_map = dict(zip(df_clean["id"], df_clean["nome"]))
    df_series["gerencia"] = df_series["uc_id"].map(ger_map).fillna(df_series["gerencia"])
    df_series["uc_nome"] = df_series["uc_id"].map(nome_map).fillna(df_series["uc_nome"])
    df_series.to_csv(csv_series, index=False, encoding="utf-8")
    print(f"Série histórica atualizada com gerências oficiais em: {csv_series}")

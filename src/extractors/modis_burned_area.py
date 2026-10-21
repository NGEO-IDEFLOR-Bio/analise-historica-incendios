"""
Extrator de Cicatrizes de Queimada Recentes (2024 a 2026) via Google Earth Engine (MODIS MCD64A1).
Permite estender a série histórica de 1985-2023 até o ano corrente com alta performance.
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import pandas as pd
import ee

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import GEOJSON_UCS, CSV_METADATA_UCS, DATA_PROCESSED
from src.gee_auth import init_gee
from src.extractors.mapbiomas_fogo import get_ee_geometry

ASSET_MODIS_BURNED_AREA = "MODIS/061/MCD64A1"

def extract_modis_annual_uc(
    feat: Dict[str, Any],
    ano: int,
    scale: int = 500
) -> float:
    """Extrai a área queimada em hectares para uma UC e um ano específico."""
    geom = get_ee_geometry(feat)
    start_date = f"{ano}-01-01"
    end_date = f"{ano}-12-31"

    col = ee.ImageCollection(ASSET_MODIS_BURNED_AREA).filterDate(start_date, end_date)
    if col.size().getInfo() == 0:
        return 0.0

    burned_mask = col.select("BurnDate").map(lambda img: img.gt(0)).max().unmask(0)
    pixel_ha = ee.Image.pixelArea().divide(10000.0)
    burned_ha_img = burned_mask.multiply(pixel_ha)

    stats = burned_ha_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geom,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True
    ).getInfo()

    val = stats.get("BurnDate") if stats else 0.0
    return float(val) if val is not None else 0.0

def extract_recent_series(
    anos: List[int] = [2024, 2025, 2026],
    save_csv: bool = True
) -> pd.DataFrame:
    """
    Extrai as cicatrizes de queimada de anos recentes para todas as 29 UCs Estaduais
    e consolida em DataFrame compatível com a série histórica MapBiomas.
    """
    init_gee()

    with open(GEOJSON_UCS, "r", encoding="utf-8") as f:
        data = json.load(f)

    df_meta = pd.read_csv(CSV_METADATA_UCS)
    meta_dict = df_meta.set_index("id").to_dict("index")

    rows = []
    total_ops = len(data["features"]) * len(anos)
    print(f"Iniciando extração recente GEE ({len(anos)} anos x 29 UCs = {total_ops} consultas)...")

    for feat in data["features"]:
        uid = int(feat["properties"]["id"])
        meta = meta_dict.get(uid, {})
        uc_nome = meta.get("nome", feat["properties"].get("nome_", f"UC {uid}"))
        gerencia = meta.get("gerencia", feat["properties"].get("gerencia", ""))
        grupo = meta.get("grupo", feat["properties"].get("grupo", ""))
        categoria = meta.get("categoria", feat["properties"].get("categoria", ""))
        ano_criacao = meta.get("ano_criacao")
        area_uc_ha = float(meta.get("area_ha", feat["properties"].get("area_ha", 0.0)))

        for ano in anos:
            try:
                burned_ha = extract_modis_annual_uc(feat, ano)
            except Exception as e:
                print(f"Erro ao extrair UC {uid} ({uc_nome}) ano {ano}: {e}")
                burned_ha = 0.0

            taxa_pct = (burned_ha / area_uc_ha * 100.0) if area_uc_ha > 0 else 0.0
            
            delta_anos = None
            status_marco = "Pós-Criação"
            if ano_criacao and not pd.isna(ano_criacao):
                ano_criacao = int(ano_criacao)
                delta_anos = ano - ano_criacao
                status_marco = "Pós-Criação" if delta_anos >= 0 else "Pré-Criação"

            rows.append({
                "uc_id": uid,
                "uc_nome": uc_nome,
                "gerencia": gerencia,
                "grupo": grupo,
                "categoria": categoria,
                "ano_criacao": ano_criacao,
                "ano": ano,
                "burned_ha": round(burned_ha, 2),
                "area_uc_ha": round(area_uc_ha, 2),
                "taxa_queimada_pct": round(taxa_pct, 4),
                "delta_anos_criacao": delta_anos,
                "status_marco": status_marco
            })

    df_recent = pd.DataFrame(rows)

    if save_csv:
        output_csv = DATA_PROCESSED / f"modis_mcd64a1_series_{min(anos)}_{max(anos)}.csv"
        df_recent.to_csv(output_csv, index=False, encoding="utf-8")
        print(f"Série recente salva em: {output_csv}")

    return df_recent

def build_extended_full_series(
    anos_recentes: List[int] = [2024, 2025, 2026],
    force_gee: bool = False
) -> pd.DataFrame:
    """
    Gera a série histórica completa unificada de 1985 até 2026:
    - 1985 a 2023: MapBiomas Fogo Coleção 3 (30m)
    - 2024 a 2026: MODIS MCD64A1 (500m)
    """
    csv_recent = DATA_PROCESSED / f"modis_mcd64a1_series_{min(anos_recentes)}_{max(anos_recentes)}.csv"
    csv_full = DATA_PROCESSED / "mapbiomas_fogo_series_1985_2026.csv"
    csv_historic = DATA_PROCESSED / "mapbiomas_fogo_series_1985_2023.csv"

    if not csv_recent.exists() or force_gee:
        df_recent = extract_recent_series(anos=anos_recentes, save_csv=True)
    else:
        df_recent = pd.read_csv(csv_recent)

    df_historic = pd.read_csv(csv_historic)
    
    # Concatenar séries
    df_full = pd.concat([df_historic, df_recent], ignore_index=True)
    df_full = df_full.sort_values(["uc_id", "ano"]).reset_index(drop=True)
    
    df_full.to_csv(csv_full, index=False, encoding="utf-8")
    print(f"Série estendida unificada (1985-{max(anos_recentes)}) salva com sucesso em: {csv_full}")
    return df_full

if __name__ == "__main__":
    build_extended_full_series(force_gee=True)

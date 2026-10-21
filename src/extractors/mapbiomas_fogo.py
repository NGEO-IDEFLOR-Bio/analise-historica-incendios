"""
Extrator de Séries Temporais do MapBiomas Fogo via Google Earth Engine (GEE).
Extrai a área queimada anual (1985-2023) para as Unidades de Conservação do IDEFLOR-Bio.
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import time
import pandas as pd
import ee

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import (
    ASSET_MAPBIOMAS_FOGO_ANUAL,
    DATA_PROCESSED,
    DATA_OUTPUT
)
from src.gee_auth import init_gee
from src.ucs import UCDatabase

def strip_z(coords):
    """Remove coordenadas Z (elevação/3D) de listas de coordenadas GeoJSON."""
    if isinstance(coords[0], (int, float)):
        return coords[:2]
    return [strip_z(c) for c in coords]

def get_ee_geometry(feat: Dict[str, Any]) -> ee.Geometry:
    """Converte geometria de feature GeoJSON para ee.Geometry 2D."""
    geom = feat["geometry"]
    clean_coords = strip_z(geom["coordinates"])
    return ee.Geometry({
        "type": geom["type"],
        "coordinates": clean_coords
    })

def extract_uc_series(
    uc_props: Dict[str, Any],
    feat: Dict[str, Any],
    scale: int = 60
) -> List[Dict[str, Any]]:
    """Extrai a série temporal 1985-2023 de cicatrizes de fogo para uma única UC."""
    ee_geom = get_ee_geometry(feat)
    img = ee.Image(ASSET_MAPBIOMAS_FOGO_ANUAL)
    
    # Área em hectares de cada pixel queimado
    pixel_area_ha = ee.Image.pixelArea().divide(10000.0)
    burned_bands = img.gt(0).multiply(pixel_area_ha)

    stats = burned_bands.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=ee_geom,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True
    )
    res = stats.getInfo()

    uc_id = uc_props.get("id")
    uc_nome = uc_props.get("nome") or uc_props.get("name")
    gerencia = uc_props.get("gerencia")
    grupo = uc_props.get("grupo")
    categoria = uc_props.get("categoria")
    ano_criacao = uc_props.get("ano_criacao")
    area_total_ha = uc_props.get("area_ha", 0.0)

    rows = []
    for band_name, val_ha in res.items():
        if not band_name.startswith("burned_coverage_"):
            continue
        try:
            ano = int(band_name.replace("burned_coverage_", ""))
        except ValueError:
            continue

        burned_ha = float(val_ha or 0.0)
        pct = (burned_ha / area_total_ha * 100.0) if area_total_ha > 0 else 0.0
        
        # Classificação temporal em relação ao decreto de criação
        if ano_criacao:
            delta_anos = ano - int(ano_criacao)
            status_marco = "Pós-Criação" if ano >= int(ano_criacao) else "Pré-Criação"
        else:
            delta_anos = None
            status_marco = "Indefinido"

        rows.append({
            "uc_id": uc_id,
            "uc_nome": uc_nome,
            "gerencia": gerencia,
            "grupo": grupo,
            "categoria": categoria,
            "ano_criacao": ano_criacao,
            "ano": ano,
            "burned_ha": round(burned_ha, 2),
            "area_uc_ha": round(area_total_ha, 2),
            "taxa_queimada_pct": round(pct, 4),
            "delta_anos_criacao": delta_anos,
            "status_marco": status_marco
        })

    return sorted(rows, key=lambda x: x["ano"])

def extract_all_ucs(scale: int = 60, output_filename: str = "mapbiomas_fogo_series_1985_2023.csv") -> pd.DataFrame:
    """Extrai e consolida a série temporal completa para todas as 29 UCs."""
    init_gee()
    db = UCDatabase()
    df_meta = db.df
    all_rows = []

    print(f"=== Iniciando extração GEE: {len(df_meta)} UCs (Escala: {scale}m) ===")
    t0 = time.time()

    for idx, row in df_meta.iterrows():
        uc_id = int(row["id"])
        uc_nome = row["nome"]
        gerencia = row["gerencia"]
        print(f"[{idx+1}/{len(df_meta)}] Extraindo UC {uc_id}: {uc_nome} ({gerencia})...", end=" ", flush=True)
        
        feat = db.get_geometry_by_id(uc_id)
        if not feat:
            print("PULADO (Geometria não encontrada)")
            continue

        t_uc = time.time()
        try:
            uc_series = extract_uc_series(row.to_dict(), feat, scale=scale)
            all_rows.extend(uc_series)
            print(f"OK ({time.time() - t_uc:.1f}s)")
        except Exception as e:
            print(f"ERRO: {e}")

    df_consolidado = pd.DataFrame(all_rows)
    out_csv = DATA_PROCESSED / output_filename
    out_json = DATA_PROCESSED / output_filename.replace(".csv", ".json")
    
    df_consolidado.to_csv(out_csv, index=False, encoding="utf-8-sig")
    df_consolidado.to_json(out_json, orient="records", force_ascii=False, indent=2)

    tempo_total = time.time() - t0
    print(f"\nExtração concluída com sucesso em {tempo_total:.1f}s!")
    print(f"Total de registros anuais extraídos: {len(df_consolidado)}")
    print(f"Arquivo salvo em: {out_csv}")
    
    return df_consolidado

if __name__ == "__main__":
    extract_all_ucs(scale=90)

"""
Módulo de mapeamento espacial (GeoPandas + Matplotlib e Folium interativo).
"""
from typing import Optional, Dict, Any
from pathlib import Path
import json
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
import folium
import branca.colormap as cm

from src.config import GEOJSON_UCS, DATA_OUTPUT
from src.viz.theme import apply_ggplot_theme, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED

def plot_static_map(df_series: pd.DataFrame, figsize=(11, 9)):
    """Gera mapa coroplético estático com qualidade editorial (GeoPandas + Matplotlib)."""
    apply_ggplot_theme()
    
    # Carregar GeoDataFrame
    gdf = gpd.read_file(GEOJSON_UCS)
    
    # Resumo de queima por UC
    uc_stats = df_series.groupby("uc_id").agg(
        taxa_media_pct=("taxa_queimada_pct", "mean"),
        taxa_max_pct=("taxa_queimada_pct", "max"),
        burned_ha_total=("burned_ha", "sum")
    ).reset_index()

    gdf = gdf.merge(uc_stats, left_on="id", right_on="uc_id", how="left")

    fig, ax = plt.subplots(figsize=figsize)
    
    # Plotar UCs coloridas pela taxa média
    cmap = plt.cm.YlOrRd
    gdf.plot(
        column="taxa_media_pct",
        cmap=cmap,
        linewidth=0.8,
        edgecolor="#374151",
        legend=True,
        legend_kwds={
            "label": "Taxa Média de Queima (% da área da UC/ano, 1985–2023)",
            "orientation": "horizontal",
            "shrink": 0.65,
            "pad": 0.05
        },
        ax=ax
    )

    ax.set_title("Pressão Histórica de Queimadas nas 29 UCs do Pará (IDEFLOR-Bio)", fontsize=13, fontweight="bold", pad=12)
    ax.set_axis_off()

    plt.figtext(
        0.15, 0.04,
        "Fonte: MapBiomas Fogo (Coleção 3). Projeção: SIRGAS 2000 (EPSG:4674).",
        fontsize=8, color=COLOR_TEXT_MUTED
    )
    plt.tight_layout()
    return fig, ax

def create_interactive_folium_map(df_series: pd.DataFrame, save_html: bool = True) -> folium.Map:
    """Gera mapa interativo Folium com tooltips detalhadas e escala contínua de cores."""
    with open(GEOJSON_UCS, "r", encoding="utf-8") as f:
        geo_data = json.load(f)

    uc_stats = df_series.groupby("uc_id").agg(
        taxa_media_pct=("taxa_queimada_pct", "mean"),
        burned_ha_total=("burned_ha", "sum")
    ).reset_index()
    stats_map = {row["uc_id"]: row for _, row in uc_stats.iterrows()}

    # Adicionar estatísticas nas propriedades do GeoJSON
    for feat in geo_data["features"]:
        uid = feat["properties"].get("id")
        stat = stats_map.get(uid)
        if stat is not None:
            feat["properties"]["taxa_media_pct"] = round(float(stat["taxa_media_pct"]), 2)
            feat["properties"]["burned_ha_total"] = round(float(stat["burned_ha_total"]), 1)
        else:
            feat["properties"]["taxa_media_pct"] = 0.0
            feat["properties"]["burned_ha_total"] = 0.0

    # Centro aproximado do Pará
    m = folium.Map(
        location=[-3.8, -52.5],
        zoom_start=6,
        tiles="OpenStreetMap"
    )

    max_taxa = max([f["properties"]["taxa_media_pct"] for f in geo_data["features"]] or [1.0])
    colormap = cm.LinearColormap(
        colors=["#FFFFB2", "#FECC5C", "#FD8D3C", "#F03B20", "#BD0026"],
        vmin=0.0,
        vmax=max(max_taxa, 5.0),
        caption="Taxa Média Anual de Queima (% da UC / ano, 1985–2023)"
    )
    colormap.add_to(m)

    def style_fn(feature):
        val = feature["properties"].get("taxa_media_pct", 0.0)
        return {
            "fillColor": colormap(val),
            "color": "#1F2937",
            "weight": 1.2,
            "fillOpacity": 0.75
        }

    def highlight_fn(feature):
        return {
            "color": "#000000",
            "weight": 2.5,
            "fillOpacity": 0.95
        }

    folium.GeoJson(
        geo_data,
        name="Unidades de Conservação",
        style_function=style_fn,
        highlight_function=highlight_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "gerencia", "categoria", "grupo", "criacao", "area_ha", "taxa_media_pct", "burned_ha_total"],
            aliases=[
                "Unidade:",
                "Gerência:",
                "Categoria:",
                "Grupo SNUC:",
                "Data Criação:",
                "Área (ha):",
                "Taxa Média Queima (%/ano):",
                "Área Queimada Total 1985-2023 (ha):"
            ],
            localize=True,
            sticky=True
        )
    ).add_to(m)

    folium.LayerControl().add_to(m)

    if save_html:
        out_html = DATA_OUTPUT / "mapa_interativo_fogo_ucs.html"
        m.save(str(out_html))
        print(f"Mapa interativo salvo em: {out_html}")

    return m

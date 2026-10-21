"""
Modulo de cartografia e mapeamento espacial.
Gera prancha cartografica profissional em layout de atlas (GeoPandas e Matplotlib)
e mapa interativo para navegacao vetorial em tela cheia (Folium).
"""
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import folium
import branca.colormap as cm

from src.config import (
    GEOJSON_UCS,
    GEOJSON_PARA,
    GEOJSON_BRASIL_UFS_SIMP,
    GEOJSON_AMERICA_DO_SUL_SIMP,
    DATA_OUTPUT
)
from src.viz.theme import (
    apply_ggplot_theme,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED
)

def _draw_scale_bar(ax, x0: float, y0: float, length_km: float = 300.0, lat_ref: float = -4.0):
    """
    Desenha uma barra de escala grafica cartografica com blocos alternados em preto e branco.
    Calcula a conversao aproximada de graus para quilometros na latitude de referencia.
    """
    # 1 grau de longitude na latitude lat_ref (em km)
    km_per_deg = 111.32 * np.cos(np.radians(lat_ref))
    length_deg = length_km / km_per_deg
    height_deg = 0.18

    # Desenha dois segmentos (0 a length/2 e length/2 a length)
    half_deg = length_deg / 2.0
    half_km = length_km / 2.0

    # Fundo branco sutil para legibilidade
    bg = patches.Rectangle(
        (x0 - 0.2, y0 - 0.45),
        length_deg + 1.2,
        height_deg + 0.95,
        facecolor="#FFFFFF",
        edgecolor="#CBD5E1",
        linewidth=0.6,
        alpha=0.92,
        zorder=20
    )
    ax.add_patch(bg)

    # Bloco 1 (preto)
    rect1 = patches.Rectangle((x0, y0), half_deg, height_deg, facecolor="#1E293B", edgecolor="#1E293B", zorder=21)
    # Bloco 2 (branco)
    rect2 = patches.Rectangle((x0 + half_deg, y0), half_deg, height_deg, facecolor="#F8FAFC", edgecolor="#1E293B", zorder=21)
    ax.add_patch(rect1)
    ax.add_patch(rect2)

    # Rotulos de distancia
    ax.text(x0, y0 - 0.25, "0", ha="center", va="top", fontsize=7.5, color="#1E293B", fontweight="bold", zorder=22)
    ax.text(x0 + half_deg, y0 - 0.25, f"{int(half_km)}", ha="center", va="top", fontsize=7.5, color="#1E293B", fontweight="bold", zorder=22)
    ax.text(x0 + length_deg, y0 - 0.25, f"{int(length_km)} km", ha="center", va="top", fontsize=7.5, color="#1E293B", fontweight="bold", zorder=22)

def _draw_north_arrow(ax, x: float, y: float, size: float = 0.8):
    """Desenha indicador de norte cartografico minimalista."""
    # Fundo circular
    circle = patches.Circle((x, y), size * 0.9, facecolor="#FFFFFF", edgecolor="#CBD5E1", linewidth=0.6, alpha=0.92, zorder=20)
    ax.add_patch(circle)

    # Metade esquerda (escura)
    poly_left = patches.Polygon([[x, y + size * 0.65], [x - size * 0.3, y - size * 0.4], [x, y]], facecolor="#0F172A", edgecolor="#0F172A", zorder=21)
    # Metade direita (clara)
    poly_right = patches.Polygon([[x, y + size * 0.65], [x + size * 0.3, y - size * 0.4], [x, y]], facecolor="#F8FAFC", edgecolor="#0F172A", zorder=21)
    
    ax.add_patch(poly_left)
    ax.add_patch(poly_right)
    ax.text(x, y + size * 0.72, "N", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#0F172A", zorder=22)

def plot_static_map(
    df_series: pd.DataFrame,
    figsize: Tuple[int, int] = (15, 11),
    save_path: Optional[Path] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Gera prancha cartografica de alto padrao editorial com:
    - Contexto da America do Sul e estados vizinhos
    - Limites oficiais do Estado do Para
    - As 29 Unidades de Conservacao coloridas por taxa media anual de queima
    - Inset de localizacao continental (mapa de enquadramento)
    - Barra de escala grafica, rosa dos ventos e grade de coordenadas (graticules)
    """
    apply_ggplot_theme()

    # 1. Carregamento e preparacao dos dados espaciais
    gdf_ucs = gpd.read_file(GEOJSON_UCS)
    gdf_para = gpd.read_file(GEOJSON_PARA)
    
    # Priorizar bases simplificadas para performance; fallback para raw se necessario
    ufs_path = GEOJSON_BRASIL_UFS_SIMP if GEOJSON_BRASIL_UFS_SIMP.exists() else GEOJSON_BRASIL_UFS
    sa_path = GEOJSON_AMERICA_DO_SUL_SIMP if GEOJSON_AMERICA_DO_SUL_SIMP.exists() else GEOJSON_AMERICA_DO_SUL
    gdf_ufs = gpd.read_file(ufs_path)
    gdf_sa = gpd.read_file(sa_path)

    # Consolidacao das metricas de fogo por UC
    uc_stats = df_series.groupby("uc_id").agg(
        taxa_media_pct=("taxa_queimada_pct", "mean"),
        taxa_max_pct=("taxa_queimada_pct", "max"),
        burned_ha_total=("burned_ha", "sum")
    ).reset_index()
    gdf_ucs = gdf_ucs.merge(uc_stats, left_on="id", right_on="uc_id", how="left")

    # 2. Criacao da figura principal
    fig, ax = plt.subplots(figsize=figsize, facecolor="#F8FAFC")
    ax.set_facecolor("#E0F2FE")  # Fundo oceanico suave

    # Enquadramento geografico do mapa principal (com margem de respiro)
    xlim = (-59.2, -45.6)
    ylim = (-10.4, 3.2)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    # 3. Camadas de Fundo Geografico
    # 3.1. America do Sul (paises)
    gdf_sa.plot(ax=ax, facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.7, zorder=2)

    # 3.2. Estados Brasileiros vizinhos
    gdf_ufs.plot(ax=ax, facecolor="#F8FAFC", edgecolor="#D1D5DB", linewidth=0.7, zorder=3)

    # 3.3. Estado do Para (destaque do territorio estadual)
    gdf_para.plot(ax=ax, facecolor="#FFFFFF", edgecolor="#334155", linewidth=1.6, zorder=4)

    # 4. Camada Tematica: As 29 Unidades de Conservacao
    cmap = plt.cm.YlOrRd
    norm = mcolors.Normalize(vmin=0.0, vmax=max(gdf_ucs["taxa_media_pct"].max(), 5.0))

    gdf_ucs.plot(
        ax=ax,
        column="taxa_media_pct",
        cmap=cmap,
        norm=norm,
        edgecolor="#1E293B",
        linewidth=0.75,
        alpha=0.92,
        zorder=10
    )

    # 5. Rotulos Geograficos dos Estados e Paises Vizinhos
    rotulos_vizinhos = [
        {"texto": "AMAZONAS", "pos": (-58.3, -4.5), "rot": 0},
        {"texto": "MATO GROSSO", "pos": (-54.5, -10.0), "rot": 0},
        {"texto": "TOCANTINS", "pos": (-48.2, -7.5), "rot": 0},
        {"texto": "MARANHÃO", "pos": (-46.3, -3.8), "rot": 0},
        {"texto": "AMAPÁ", "pos": (-51.8, 1.6), "rot": 0},
        {"texto": "RORAIMA", "pos": (-58.8, 1.2), "rot": 0},
        {"texto": "SURINAME", "pos": (-56.0, 2.7), "rot": 0},
        {"texto": "GUIANA\nFRANCESA", "pos": (-53.0, 2.8), "rot": 0},
        {"texto": "OCEANO ATLÂNTICO", "pos": (-47.5, 1.2), "rot": -25, "cor": "#0369A1", "estilo": "italic"},
    ]

    for item in rotulos_vizinhos:
        # Exibir somente se dentro dos limites de exibicao
        if xlim[0] <= item["pos"][0] <= xlim[1] and ylim[0] <= item["pos"][1] <= ylim[1]:
            ax.text(
                item["pos"][0],
                item["pos"][1],
                item["texto"],
                fontsize=8.0,
                fontweight="bold",
                color=item.get("cor", "#94A3B8"),
                fontstyle=item.get("estilo", "normal"),
                rotation=item.get("rot", 0),
                ha="center",
                va="center",
                zorder=6
            )

    # 6. Grade Geografica (Graticules) com rotulos de graus
    x_ticks = np.arange(-58, -44, 4)
    y_ticks = np.arange(-10, 4, 2)
    ax.set_xticks(x_ticks)
    ax.set_yticks(y_ticks)
    ax.set_xticklabels([f"{abs(int(x))}°W" for x in x_ticks], fontsize=8.5, color=COLOR_TEXT_MUTED)
    ax.set_yticklabels([f"{int(y)}°N" if y > 0 else (f"{abs(int(y))}°S" if y < 0 else "0°") for y in y_ticks], fontsize=8.5, color=COLOR_TEXT_MUTED)
    ax.grid(True, linestyle=":", color="#94A3B8", alpha=0.5, zorder=5)

    # 7. Barra de Escala e Indicador de Norte
    _draw_scale_bar(ax, x0=-49.8, y0=-9.8, length_km=300.0, lat_ref=-4.0)
    _draw_north_arrow(ax, x=-46.8, y=1.9, size=0.65)

    # 8. Inset Map: Enquadramento Continental (America do Sul e Brasil)
    # Posicionado no canto inferior esquerdo
    ax_inset = inset_axes(
        ax,
        width="26%",
        height="28%",
        loc="lower left",
        bbox_to_anchor=(0.02, 0.03, 1, 1),
        bbox_transform=ax.transAxes,
        borderpad=0
    )
    ax_inset.set_facecolor("#E0F2FE")

    # Desenha America do Sul e Brasil no Inset
    gdf_sa.plot(ax=ax_inset, facecolor="#E2E8F0", edgecolor="#CBD5E1", linewidth=0.4)
    gdf_ufs.plot(ax=ax_inset, facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.3)
    gdf_para.plot(ax=ax_inset, facecolor="#D84315", edgecolor="#BF360C", linewidth=0.8)

    # Retangulo demarcador da regiao do mapa principal
    rect_extent = patches.Rectangle(
        (xlim[0], ylim[0]),
        xlim[1] - xlim[0],
        ylim[1] - ylim[0],
        linewidth=1.0,
        edgecolor="#B91C1C",
        facecolor="none",
        linestyle="--",
        zorder=10
    )
    ax_inset.add_patch(rect_extent)

    ax_inset.set_xlim(-82, -34)
    ax_inset.set_ylim(-56, 14)
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])
    for spine in ax_inset.spines.values():
        spine.set_color("#64748B")
        spine.set_linewidth(0.8)
    ax_inset.set_title("Localizacao no Brasil", fontsize=7.5, fontweight="bold", pad=3, color="#1E293B")

    # 9. Barra de Legenda Tematica
    cax = inset_axes(
        ax,
        width="38%",
        height="2.5%",
        loc="lower left",
        bbox_to_anchor=(0.02, 0.35, 1, 1),
        bbox_transform=ax.transAxes,
        borderpad=0
    )
    cbar = plt.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=cax,
        orientation="horizontal"
    )
    cbar.set_label("Taxa Media Anual de Queima (% da area da UC / ano, 1985 a 2023)", fontsize=8.0, fontweight="bold", color="#1E293B", labelpad=5)
    cbar.ax.tick_params(labelsize=7.5, color="#1E293B")
    cax.set_facecolor("#FFFFFF")

    # 10. Titulos e Carimbo Cartografico Oficial
    fig.text(
        0.05, 0.95,
        "SISTEMA ESTADUAL DE UNIDADES DE CONSERVACAO DO PARA (IDEFLOR-BIO)",
        fontsize=14, fontweight="bold", color="#0F172A", ha="left"
    )
    fig.text(
        0.05, 0.925,
        "Distribuicao Geografica e Pressao Historica de Cicatrizes de Queimada (1985 a 2023)",
        fontsize=10.5, color="#475569", ha="left"
    )
    fig.text(
        0.05, 0.015,
        "Sistema Geodesico de Referencia: SIRGAS 2000 (EPSG:4674) | Dados de Fogo: MapBiomas Fogo Colecao 3 (Landsat 30m) | Malha Territorial Oficial: IDEFLOR-Bio e IBGE",
        fontsize=7.5, color="#64748B", ha="left"
    )

    plt.subplots_adjust(top=0.91, bottom=0.04, left=0.04, right=0.98)

    if save_path:
        fig.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
        print(f"Prancha cartografica salva com sucesso em: {save_path}")

    return fig, ax

def create_interactive_folium_map(df_series: pd.DataFrame, save_html: bool = True) -> folium.Map:
    """Gera mapa interativo Folium com tooltips detalhadas, limites estaduais e escala continua."""
    with open(GEOJSON_UCS, "r", encoding="utf-8") as f:
        geo_data = json.load(f)

    # Carregar limite do Para
    with open(GEOJSON_PARA, "r", encoding="utf-8") as f:
        geo_para = json.load(f)

    # Estatisticas agregadas por UC
    uc_stats = df_series.groupby("uc_id").agg(
        taxa_media_pct=("taxa_queimada_pct", "mean"),
        burned_ha_total=("burned_ha", "sum")
    ).reset_index()
    stats_map = {row["uc_id"]: row for _, row in uc_stats.iterrows()}

    for feat in geo_data["features"]:
        uid = feat["properties"].get("id")
        stat = stats_map.get(uid)
        if stat is not None:
            feat["properties"]["taxa_media_pct"] = round(float(stat["taxa_media_pct"]), 2)
            feat["properties"]["burned_ha_total"] = round(float(stat["burned_ha_total"]), 1)
        else:
            feat["properties"]["taxa_media_pct"] = 0.0
            feat["properties"]["burned_ha_total"] = 0.0

    # Inicializar mapa centralizado no Estado do Para
    m = folium.Map(
        location=[-3.8, -52.5],
        zoom_start=6,
        tiles="OpenStreetMap"
    )

    # 1. Camada de Limite Estadual do Para
    folium.GeoJson(
        geo_para,
        name="Limite Estadual do Para",
        style_function=lambda x: {
            "fillColor": "none",
            "color": "#1E293B",
            "weight": 2.2,
            "dashArray": "4, 4"
        }
    ).add_to(m)

    # 2. Escala de cores continua para as UCs
    max_taxa = max([f["properties"]["taxa_media_pct"] for f in geo_data["features"]] or [1.0])
    colormap = cm.LinearColormap(
        colors=["#FFFFB2", "#FECC5C", "#FD8D3C", "#F03B20", "#BD0026"],
        vmin=0.0,
        vmax=max(max_taxa, 5.0),
        caption="Taxa Media Anual de Queima (% da UC / ano, 1985 a 2023)"
    )
    colormap.add_to(m)

    def style_fn(feature):
        val = feature["properties"].get("taxa_media_pct", 0.0)
        return {
            "fillColor": colormap(val),
            "color": "#0F172A",
            "weight": 1.2,
            "fillOpacity": 0.8
        }

    def highlight_fn(feature):
        return {
            "color": "#000000",
            "weight": 2.8,
            "fillOpacity": 0.95
        }

    # 3. Camada das Unidades de Conservacao
    folium.GeoJson(
        geo_data,
        name="Unidades de Conservacao (IDEFLOR-Bio)",
        style_function=style_fn,
        highlight_function=highlight_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "gerencia", "categoria", "grupo", "criacao", "area_ha", "taxa_media_pct", "burned_ha_total"],
            aliases=[
                "Unidade:",
                "Gerencia Regional:",
                "Categoria:",
                "Grupo SNUC:",
                "Data de Criacao:",
                "Area Total (ha):",
                "Taxa Media de Queima (%/ano):",
                "Area Queimada Total 1985-2023 (ha):"
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

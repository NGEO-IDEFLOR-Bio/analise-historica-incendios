"""
Modulo de cartografia e mapeamento espacial institucional.
Padronizado no layout cartografico oficial do NGEO/IDEFLOR-Bio (Prancha Paisagem A4/A3):
- Cabecalho superior com titulo oficial
- Painel cartografico principal (corpo esquerdo)
- Coluna lateral direita:
  * Painel de Enquadramento Geografico / Localizacao
  * Painel de Legenda Tematica estruturada
  * Carimbo Institucional (Metadados, Data, Projecao e Creditos)
- Mapa Interativo baseado em MapLibre GL JS com filtros funcionais por Gerencia Regional,
  Grupo SNUC e slider temporal, sem dependencia de chaves pagas de tiles.
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
import matplotlib.gridspec as gridspec

from src.config import (
    GEOJSON_UCS,
    GEOJSON_PARA,
    GEOJSON_BRASIL_UFS_SIMP,
    GEOJSON_AMERICA_DO_SUL_SIMP,
    GEOJSON_BRASIL_UFS,
    GEOJSON_AMERICA_DO_SUL,
    DATA_OUTPUT,
    SIGLAS_GERENCIAS
)
from src.viz.theme import apply_ggplot_theme

def _draw_scale_bar(ax, x0: float, y0: float, length_km: float = 300.0, lat_ref: float = -4.0):
    """Desenha barra de escala grafica alternada (preto e branco)."""
    km_per_deg = 111.32 * np.cos(np.radians(lat_ref))
    length_deg = length_km / km_per_deg
    height_deg = 0.16
    half_deg = length_deg / 2.0
    half_km = length_km / 2.0

    rect1 = patches.Rectangle((x0, y0), half_deg, height_deg, facecolor="#000000", edgecolor="#000000", zorder=21)
    rect2 = patches.Rectangle((x0 + half_deg, y0), half_deg, height_deg, facecolor="#FFFFFF", edgecolor="#000000", zorder=21)
    ax.add_patch(rect1)
    ax.add_patch(rect2)

    ax.text(x0, y0 + height_deg + 0.08, "0", ha="center", va="bottom", fontsize=8, color="#000000", fontweight="bold", zorder=22)
    ax.text(x0 + half_deg, y0 + height_deg + 0.08, f"{int(half_km)}", ha="center", va="bottom", fontsize=8, color="#000000", fontweight="bold", zorder=22)
    ax.text(x0 + length_deg, y0 + height_deg + 0.08, f"{int(length_km)} km", ha="center", va="bottom", fontsize=8, color="#000000", fontweight="bold", zorder=22)

def _draw_north_arrow(ax, x: float, y: float, size: float = 0.75):
    """Desenha indicador de norte cartografico institucional."""
    poly_left = patches.Polygon([[x, y + size * 0.7], [x - size * 0.3, y - size * 0.4], [x, y]], facecolor="#000000", edgecolor="#000000", zorder=21)
    poly_right = patches.Polygon([[x, y + size * 0.7], [x + size * 0.3, y - size * 0.4], [x, y]], facecolor="#FFFFFF", edgecolor="#000000", zorder=21)
    ax.add_patch(poly_left)
    ax.add_patch(poly_right)
    ax.text(x, y + size * 0.8, "N", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#000000", zorder=22)

def plot_static_map(
    df_series: pd.DataFrame,
    figsize: Tuple[int, int] = (16, 11),
    save_path: Optional[Path] = None
) -> Tuple[plt.Figure, Any]:
    """
    Gera prancha cartografica oficial no padrao institucional NGEO/IDEFLOR-Bio:
    - Cabecalho horizontal superior (titulo institucional)
    - Painel principal esquerdo (mapa tematico com grade, limites e UCs)
    - Coluna lateral direita:
      * Painel superior: Enquadramento geografico (America do Sul, Brasil e Para)
      * Painel intermediario: Legenda tematica estruturada com classes de queima
      * Painel inferior: Carimbo oficial (dados tecnicos, datum, projecao e autoria)
    """
    apply_ggplot_theme()

    gdf_ucs = gpd.read_file(GEOJSON_UCS)
    gdf_para = gpd.read_file(GEOJSON_PARA)
    
    ufs_path = GEOJSON_BRASIL_UFS_SIMP if GEOJSON_BRASIL_UFS_SIMP.exists() else GEOJSON_BRASIL_UFS
    sa_path = GEOJSON_AMERICA_DO_SUL_SIMP if GEOJSON_AMERICA_DO_SUL_SIMP.exists() else GEOJSON_AMERICA_DO_SUL
    gdf_ufs = gpd.read_file(ufs_path)
    gdf_sa = gpd.read_file(sa_path)

    uc_stats = df_series.groupby("uc_id").agg(
        taxa_media_pct=("taxa_queimada_pct", "mean"),
        taxa_max_pct=("taxa_queimada_pct", "max"),
        burned_ha_total=("burned_ha", "sum")
    ).reset_index()
    gdf_ucs = gdf_ucs.merge(uc_stats, left_on="id", right_on="uc_id", how="left")

    # Layout estruturado em grade: 1 linha de cabecalho + 2 linhas de mapa / coluna
    fig = plt.figure(figsize=figsize, facecolor="#FFFFFF")
    gs = gridspec.GridSpec(
        3, 2,
        width_ratios=[0.72, 0.28],
        height_ratios=[0.065, 0.45, 0.485],
        wspace=0.012, hspace=0.015,
        left=0.015, right=0.985, top=0.975, bottom=0.025
    )

    # 1. CABECALHO SUPERIOR (TITULO DO MAPA)
    ax_head = fig.add_subplot(gs[0, :])
    ax_head.set_facecolor("#FFFFFF")
    for spine in ax_head.spines.values():
        spine.set_color("#000000")
        spine.set_linewidth(1.5)
    ax_head.set_xticks([])
    ax_head.set_yticks([])
    ax_head.text(
        0.5, 0.58,
        "SISTEMA ESTADUAL DE UNIDADES DE CONSERVACAO DO PARA (IDEFLOR-BIO)",
        fontsize=14.5, fontweight="bold", color="#000000", ha="center", va="center"
    )
    ax_head.text(
        0.5, 0.22,
        "Distribuicao Geografica e Taxa Media Historica de Cicatrizes de Queimada (1985 a 2023)",
        fontsize=9.8, color="#334155", ha="center", va="center"
    )

    # 2. PAINEL PRINCIPAL (MAPA DO PARA E UCS)
    ax_main = fig.add_subplot(gs[1:, 0])
    ax_main.set_facecolor("#E0F2FE")  # Oceano Atlantico
    for spine in ax_main.spines.values():
        spine.set_color("#000000")
        spine.set_linewidth(1.5)

    xlim = (-59.2, -45.6)
    ylim = (-10.4, 3.2)
    ax_main.set_xlim(xlim)
    ax_main.set_ylim(ylim)

    # Camadas de fundo
    gdf_sa.plot(ax=ax_main, facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.6, zorder=2)
    gdf_ufs.plot(ax=ax_main, facecolor="#F8FAFC", edgecolor="#D1D5DB", linewidth=0.6, zorder=3)
    gdf_para.plot(ax=ax_main, facecolor="#FFFFFF", edgecolor="#000000", linewidth=1.8, zorder=4)

    # Cores discretizadas em classes para precisao cartografica
    classes_cores = [
        {"min": 0.0, "max": 0.5, "cor": "#FFFFB2", "label": "0,00% a 0,50% (Baixissima pressao)"},
        {"min": 0.5, "max": 2.0, "cor": "#FECC5C", "label": "0,51% a 2,00% (Baixa pressao)"},
        {"min": 2.0, "max": 4.0, "cor": "#FD8D3C", "label": "2,01% a 4,00% (Moderada pressao)"},
        {"min": 4.0, "max": 7.0, "cor": "#F03B20", "label": "4,01% a 7,00% (Alta pressao)"},
        {"min": 7.0, "max": 100.0, "cor": "#BD0026", "label": "Acima de 7,00% (Pressao critica)"}
    ]

    for cl in classes_cores:
        sub_gdf = gdf_ucs[(gdf_ucs["taxa_media_pct"] >= cl["min"]) & (gdf_ucs["taxa_media_pct"] < cl["max"])]
        if not sub_gdf.empty:
            sub_gdf.plot(
                ax=ax_main,
                facecolor=cl["cor"],
                edgecolor="#000000",
                linewidth=0.8,
                alpha=0.92,
                zorder=10
            )

    # Rotulos de paises e estados vizinhos
    rotulos_vizinhos = [
        {"texto": "AMAZONAS", "pos": (-58.2, -4.5)},
        {"texto": "MATO GROSSO", "pos": (-54.5, -9.9)},
        {"texto": "TOCANTINS", "pos": (-48.2, -7.5)},
        {"texto": "MARANHÃO", "pos": (-46.2, -3.8)},
        {"texto": "AMAPÁ", "pos": (-51.8, 1.8)},
        {"texto": "RORAIMA", "pos": (-58.8, 2.2)},
        {"texto": "SURINAME", "pos": (-56.0, 2.7)},
        {"texto": "GUIANA\nFRANCESA", "pos": (-53.0, 2.8)},
        {"texto": "OCEANO ATLÂNTICO", "pos": (-47.8, 1.8), "rot": -25, "cor": "#0284C7", "estilo": "italic"},
    ]
    for item in rotulos_vizinhos:
        if xlim[0] <= item["pos"][0] <= xlim[1] and ylim[0] <= item["pos"][1] <= ylim[1]:
            ax_main.text(
                item["pos"][0], item["pos"][1], item["texto"],
                fontsize=8.5, fontweight="bold", color=item.get("cor", "#64748B"),
                fontstyle=item.get("estilo", "normal"), rotation=item.get("rot", 0),
                ha="center", va="center", zorder=6
            )

    # Grade de coordenadas com rotulos
    x_ticks = np.arange(-58, -44, 4)
    y_ticks = np.arange(-10, 4, 2)
    ax_main.set_xticks(x_ticks)
    ax_main.set_yticks(y_ticks)
    ax_main.set_xticklabels([f"{abs(int(x))}°0'0\"W" for x in x_ticks], fontsize=8, color="#000000")
    ax_main.set_yticklabels([f"{int(y)}°0'0\"N" if y > 0 else (f"{abs(int(y))}°0'0\"S" if y < 0 else "0°0'0\"") for y in y_ticks], fontsize=8, color="#000000")
    ax_main.grid(True, linestyle=":", color="#64748B", alpha=0.45, zorder=5)
    ax_main.set_xlabel("")
    ax_main.set_ylabel("")

    # Rosa dos ventos e escala grafica no painel principal
    _draw_north_arrow(ax_main, x=-47.0, y=2.2, size=0.65)
    _draw_scale_bar(ax_main, x0=-57.8, y0=-9.2, length_km=300.0, lat_ref=-4.0)

    # 3. COLUNA DIREITA - PAINEL SUPERIOR: ENQUADRAMENTO GEOGRAFICO
    ax_inset = fig.add_subplot(gs[1, 1])
    ax_inset.set_facecolor("#E0F2FE")
    for spine in ax_inset.spines.values():
        spine.set_color("#000000")
        spine.set_linewidth(1.5)

    gdf_sa.plot(ax=ax_inset, facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.4)
    gdf_ufs.plot(ax=ax_inset, facecolor="#E2E8F0", edgecolor="#CBD5E1", linewidth=0.3)
    gdf_para.plot(ax=ax_inset, facecolor="#000000", edgecolor="#000000", linewidth=1.0)

    rect_extent = patches.Rectangle(
        (xlim[0], ylim[0]), xlim[1] - xlim[0], ylim[1] - ylim[0],
        linewidth=1.2, edgecolor="#DC2626", facecolor="none", linestyle="-", zorder=10
    )
    ax_inset.add_patch(rect_extent)
    ax_inset.set_xlim(-82, -34)
    ax_inset.set_ylim(-56, 14)
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])
    ax_inset.set_xlabel("")
    ax_inset.set_ylabel("")

    # Rotulos no mapa de enquadramento
    ax_inset.text(-60, 5, "América do Sul", fontsize=8.5, fontstyle="italic", color="#334155")
    ax_inset.text(-40, 0, "Oceano\nAtlântico", fontsize=8.5, fontstyle="italic", color="#0284C7", ha="center")
    ax_inset.text(-52, -4, "PA", fontsize=9, fontweight="bold", color="#FFFFFF", ha="center")
    ax_inset.text(-63, -4, "AM", fontsize=7.5, color="#64748B")
    ax_inset.text(-53, -13, "MT", fontsize=7.5, color="#64748B")
    ax_inset.text(-48, -10, "TO", fontsize=7.5, color="#64748B")
    ax_inset.text(-45, -5, "MA", fontsize=7.5, color="#64748B")
    ax_inset.text(-51, 1.5, "AP", fontsize=7.5, color="#64748B")
    ax_inset.text(-61, 2, "RR", fontsize=7.5, color="#64748B")

    # 4. COLUNA DIREITA - PAINEL INFERIOR: LEGENDA E CARIMBO INSTITUCIONAL
    ax_side = fig.add_subplot(gs[2, 1])
    ax_side.set_facecolor("#FFFFFF")
    for spine in ax_side.spines.values():
        spine.set_color("#000000")
        spine.set_linewidth(1.5)
    ax_side.set_xticks([])
    ax_side.set_yticks([])

    # Divisoria interna da lateral (separando Legenda e Carimbo)
    ax_side.axhline(0.38, color="#000000", linewidth=1.2)

    # 4.1. SECAO DA LEGENDA
    ax_side.text(0.06, 0.94, "LEGENDA", fontsize=11, fontweight="bold", color="#000000", va="top")

    y_leg = 0.86
    # Limite Estadual
    rect_pa = patches.Rectangle((0.06, y_leg - 0.015), 0.08, 0.03, facecolor="#FFFFFF", edgecolor="#000000", linewidth=1.6)
    ax_side.add_patch(rect_pa)
    ax_side.text(0.18, y_leg, "Limite Estadual do Pará", fontsize=8.5, va="center", color="#000000")

    y_leg -= 0.06
    ax_side.text(0.06, y_leg, "Taxa Média de Queima (% da UC / ano):", fontsize=8.8, fontweight="bold", color="#0F172A", va="center")

    for cl in classes_cores:
        y_leg -= 0.058
        box = patches.Rectangle((0.06, y_leg - 0.015), 0.08, 0.032, facecolor=cl["cor"], edgecolor="#000000", linewidth=0.8)
        ax_side.add_patch(box)
        ax_side.text(0.18, y_leg, cl["label"], fontsize=8.2, va="center", color="#000000")

    # 4.2. CARIMBO TECNICO / INSTITUCIONAL (RODAPE LATERAL)
    ax_side.text(0.06, 0.33, "Núcleo de Geotecnologias (NGEO)", fontsize=9.5, fontweight="bold", color="#000000")
    ax_side.text(0.06, 0.28, "Diretoria de Gestão e Monitoramento de UCs (DGBIO)", fontsize=8.5, color="#1E293B")
    ax_side.text(0.06, 0.23, "Instituto de Desenvolvimento Florestal e da Biodiversidade", fontsize=8.0, color="#475569")
    
    info_text = (
        "Base Territorial: 29 UCs Estaduais Oficiais\n"
        "Fonte do Regime de Fogo: MapBiomas Fogo (Coleção 3 - 30m)\n"
        "Série Temporal Analisada: 1985 a 2023 (39 anos)\n"
        "Sistema Geodésico: SIRGAS 2000 | Projeção Geográfica\n"
        "Data de Elaboração: Outubro de 2026"
    )
    ax_side.text(0.06, 0.04, info_text, fontsize=7.8, color="#334155", va="bottom", linespacing=1.35)

    if save_path:
        fig.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
        print(f"Prancha cartografica oficial salva com sucesso em: {save_path}")

    return fig, ax_main

def create_interactive_maplibre_map(
    df_series: pd.DataFrame,
    save_html: bool = True,
    output_path: Optional[Path] = None
) -> str:
    """
    Gera mapa interativo de alta capacidade analitica com MapLibre GL JS:
    - Utiliza camada de relevo/satelite mundial da Esri (completamente livre de chaves ou bloqueios)
    - Painel lateral de controle interativo:
      * Filtro dinamico por Gerencia Regional (GRB, GRNE, GRX, GRCN, etc.)
      * Filtro por Grupo SNUC (Protecao Integral vs. Uso Sustentavel)
      * Filtro por faixa de taxa de queima
    - Quadro de resumo analitico dinamico (recalcula area total e queima media dos poligonos visiveis)
    - Tooltip rica com dados da serie temporal completa
    """
    with open(GEOJSON_UCS, "r", encoding="utf-8") as f:
        geo_ucs = json.load(f)

    with open(GEOJSON_PARA, "r", encoding="utf-8") as f:
        geo_para = json.load(f)

    uc_stats = df_series.groupby("uc_id").agg(
        taxa_media_pct=("taxa_queimada_pct", "mean"),
        taxa_max_pct=("taxa_queimada_pct", "max"),
        burned_ha_total=("burned_ha", "sum")
    ).reset_index()
    stats_map = {int(row["uc_id"]): row for _, row in uc_stats.iterrows()}

    for feat in geo_ucs["features"]:
        uid = feat["properties"].get("id")
        stat = stats_map.get(uid)
        if stat is not None:
            feat["properties"]["taxa_media_pct"] = round(float(stat["taxa_media_pct"]), 2)
            feat["properties"]["taxa_max_pct"] = round(float(stat["taxa_max_pct"]), 2)
            feat["properties"]["burned_ha_total"] = round(float(stat["burned_ha_total"]), 1)
        else:
            feat["properties"]["taxa_media_pct"] = 0.0
            feat["properties"]["taxa_max_pct"] = 0.0
            feat["properties"]["burned_ha_total"] = 0.0

    geo_ucs_json_str = json.dumps(geo_ucs, ensure_ascii=False)
    geo_para_json_str = json.dumps(geo_para, ensure_ascii=False)

    html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Painel Interativo de Analise de Incendios nas UCs do Para</title>
  
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" />
  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>

  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ width: 100%; height: 100%; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    #map {{ width: 100%; height: 100%; position: absolute; top: 0; bottom: 0; left: 0; right: 0; }}

    /* Painel Lateral de Controle e Filtros */
    .control-panel {{
      position: absolute;
      top: 14px;
      left: 14px;
      width: 320px;
      background: rgba(255, 255, 255, 0.96);
      backdrop-filter: blur(8px);
      padding: 16px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.18);
      border: 1px solid #CBD5E1;
      z-index: 10;
      max-height: calc(100% - 28px);
      overflow-y: auto;
    }}
    .panel-title {{
      font-size: 14px;
      font-weight: 700;
      color: #0F172A;
      margin-bottom: 2px;
    }}
    .panel-sub {{
      font-size: 11px;
      color: #64748B;
      margin-bottom: 12px;
      border-bottom: 1px solid #E2E8F0;
      padding-bottom: 8px;
    }}
    .filter-group {{
      margin-bottom: 10px;
    }}
    .filter-label {{
      font-size: 11px;
      font-weight: 600;
      color: #334155;
      margin-bottom: 4px;
      display: block;
    }}
    .filter-select {{
      width: 100%;
      padding: 6px 8px;
      font-size: 12px;
      border: 1px solid #CBD5E1;
      border-radius: 4px;
      background: #FFFFFF;
      color: #0F172A;
    }}
    
    /* Metricas dinamicas */
    .stats-card {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 10px;
      margin-top: 12px;
    }}
    .stats-title {{
      font-size: 11px;
      font-weight: 700;
      color: #0F172A;
      margin-bottom: 6px;
    }}
    .stats-row {{
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      margin-bottom: 3px;
    }}
    .stats-val {{
      font-weight: 700;
      color: #D84315;
    }}

    /* Legenda Tematica */
    .legend {{
      position: absolute;
      bottom: 20px;
      right: 14px;
      background: rgba(255, 255, 255, 0.96);
      backdrop-filter: blur(8px);
      padding: 12px 16px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.18);
      border: 1px solid #CBD5E1;
      font-size: 11px;
      z-index: 10;
    }}
    .legend-title {{
      font-weight: 700;
      color: #0F172A;
      margin-bottom: 6px;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      margin-bottom: 3px;
    }}
    .legend-box {{
      width: 14px;
      height: 10px;
      border: 1px solid #000;
      margin-right: 6px;
      border-radius: 2px;
    }}

    /* Tooltip */
    .maplibregl-popup-content {{
      padding: 12px 14px;
      border-radius: 8px;
      box-shadow: 0 4px 18px rgba(0,0,0,0.25);
      border: 1px solid #CBD5E1;
      font-size: 11.5px;
      max-width: 300px;
      line-height: 1.45;
    }}
    .popup-title {{
      font-size: 13px;
      font-weight: 700;
      color: #0F172A;
      margin-bottom: 6px;
      border-bottom: 1px solid #E2E8F0;
      padding-bottom: 4px;
    }}
    .popup-row {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 2px;
    }}
    .popup-val {{
      font-weight: 600;
      color: #0F172A;
    }}
    .popup-badge {{
      background: #FEE2E2;
      color: #991B1B;
      padding: 1px 5px;
      border-radius: 3px;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <div id="map"></div>

  <!-- Painel Lateral de Filtros e Analise -->
  <div class="control-panel">
    <div class="panel-title">Painel de Analise Espacial</div>
    <div class="panel-sub">Filtros dinamicos das UCs do IDEFLOR-Bio</div>

    <div class="filter-group">
      <label class="filter-label" for="select-gerencia">Gerencia Regional:</label>
      <select id="select-gerencia" class="filter-select">
        <option value="TODAS">Todas as Gerencias (29 UCs)</option>
        <option value="GRCN-I">Calha Norte I (GRCN-I)</option>
        <option value="GRCN-II">Calha Norte II (GRCN-II)</option>
        <option value="GRCN-III">Calha Norte III (GRCN-III)</option>
        <option value="GRB">Belem (GRB)</option>
        <option value="GRTUC">Tucurui (GRTUC)</option>
        <option value="GRA">Araguaia (GRA)</option>
        <option value="GRM">Marajo (GRM)</option>
        <option value="GRNE">Nordeste (GRNE)</option>
        <option value="GRX">Xingu (GRX)</option>
      </select>
    </div>

    <div class="filter-group">
      <label class="filter-label" for="select-grupo">Grupo SNUC:</label>
      <select id="select-grupo" class="filter-select">
        <option value="TODOS">Todos os Grupos</option>
        <option value="Proteção Integral">Protecao Integral</option>
        <option value="Uso Sustentável">Uso Sustentavel</option>
      </select>
    </div>

    <div class="filter-group">
      <label class="filter-label" for="select-basemap">Camada de Fundo:</label>
      <select id="select-basemap" class="filter-select">
        <option value="gray">Esri World Gray (Cartografico Limpo)</option>
        <option value="sat">Esri World Imagery (Satelite)</option>
      </select>
    </div>

    <!-- Indicadores dos poligonos visiveis -->
    <div class="stats-card">
      <div class="stats-title">Resumo dos Poligonos Filtrados</div>
      <div class="stats-row"><span>UCs Exibidas:</span><span id="stat-count" class="stats-val">29</span></div>
      <div class="stats-row"><span>Area Protegida:</span><span id="stat-area" class="stats-val">19.950.698 ha</span></div>
      <div class="stats-row"><span>Taxa Media Queima:</span><span id="stat-taxa" class="stats-val">1,72% / ano</span></div>
    </div>
  </div>

  <!-- Legenda Tematica -->
  <div class="legend">
    <div class="legend-title">Taxa Media Anual de Queima</div>
    <div class="legend-item"><div class="legend-box" style="background: #FFFFB2;"></div><span>0,00% a 0,50% (Baixissima)</span></div>
    <div class="legend-item"><div class="legend-box" style="background: #FECC5C;"></div><span>0,51% a 2,00% (Baixa)</span></div>
    <div class="legend-item"><div class="legend-box" style="background: #FD8D3C;"></div><span>2,01% a 4,00% (Moderada)</span></div>
    <div class="legend-item"><div class="legend-box" style="background: #F03B20;"></div><span>4,01% a 7,00% (Alta)</span></div>
    <div class="legend-item"><div class="legend-box" style="background: #BD0026;"></div><span>Acima de 7,00% (Critica)</span></div>
  </div>

  <script>
    // Inicializacao MapLibre com servicos estaveis da Esri (livres de bloqueio de API key)
    const map = new maplibregl.Map({{
      container: 'map',
      style: {{
        version: 8,
        sources: {{
          'esri-gray': {{
            type: 'raster',
            tiles: [
              'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}'
            ],
            tileSize: 256,
            attribution: 'Esri, HERE, Garmin, &copy; OpenStreetMap'
          }},
          'esri-sat': {{
            type: 'raster',
            tiles: [
              'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}'
            ],
            tileSize: 256,
            attribution: 'Esri, Maxar, Earthstar Geographics'
          }}
        }},
        layers: [
          {{
            id: 'basemap-gray',
            type: 'raster',
            source: 'esri-gray',
            layout: {{ visibility: 'visible' }}
          }},
          {{
            id: 'basemap-sat',
            type: 'raster',
            source: 'esri-sat',
            layout: {{ visibility: 'none' }}
          }}
        ]
      }},
      center: [-52.5, -3.8],
      zoom: 5.6
    }});

    window.addEventListener('resize', () => map.resize());
    setTimeout(() => map.resize(), 500);

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.addControl(new maplibregl.FullscreenControl(), 'top-right');
    map.addControl(new maplibregl.ScaleControl({{ maxWidth: 120, unit: 'metric' }}), 'bottom-left');

    const ucsData = {geo_ucs_json_str};
    const paraData = {geo_para_json_str};

    map.on('load', () => {{
      map.addSource('limite-para', {{
        type: 'geojson',
        data: paraData
      }});

      map.addLayer({{
        id: 'limite-para-line',
        type: 'line',
        source: 'limite-para',
        paint: {{
          'line-color': '#0F172A',
          'line-width': 2.0,
          'line-dasharray': [3, 2]
        }}
      }});

      map.addSource('ucs-ideflor', {{
        type: 'geojson',
        data: ucsData
      }});

      // Preenchimento por classes identicas a prancha cartografica estatica
      map.addLayer({{
        id: 'ucs-fill',
        type: 'fill',
        source: 'ucs-ideflor',
        paint: {{
          'fill-color': [
            'step',
            ['get', 'taxa_media_pct'],
            '#FFFFB2',
            0.51, '#FECC5C',
            2.01, '#FD8D3C',
            4.01, '#F03B20',
            7.01, '#BD0026'
          ],
          'fill-opacity': 0.85
        }}
      }});

      map.addLayer({{
        id: 'ucs-line',
        type: 'line',
        source: 'ucs-ideflor',
        paint: {{
          'line-color': '#000000',
          'line-width': 1.0
        }}
      }});

      map.addLayer({{
        id: 'ucs-highlight',
        type: 'line',
        source: 'ucs-ideflor',
        paint: {{
          'line-color': '#000000',
          'line-width': 3.2
        }},
        filter: ['==', 'id', '']
      }});

      // Popup de Informacoes
      const popup = new maplibregl.Popup({{
        closeButton: false,
        closeOnClick: false
      }});

      map.on('mousemove', 'ucs-fill', (e) => {{
        map.getCanvas().style.cursor = 'pointer';

        if (e.features && e.features.length > 0) {{
          const props = e.features[0].properties;
          map.setFilter('ucs-highlight', ['==', 'id', props.id]);

          const taxaMedia = Number(props.taxa_media_pct || 0).toFixed(2);
          const taxaMax = Number(props.taxa_max_pct || 0).toFixed(2);
          const areaHa = Number(props.area_ha || 0).toLocaleString('pt-BR', {{ maximumFractionDigits: 0 }});
          const totalBurned = Number(props.burned_ha_total || 0).toLocaleString('pt-BR', {{ maximumFractionDigits: 0 }});

          const html = `
            <div class="popup-title">${{props.name || props.nome_}}</div>
            <div class="popup-row"><span>Gerencia:</span><span class="popup-val">${{props.gerencia || '-'}}</span></div>
            <div class="popup-row"><span>Categoria:</span><span class="popup-val">${{props.categoria || '-'}} (${{props.grupo || '-'}})</span></div>
            <div class="popup-row"><span>Ano Criacao:</span><span class="popup-val">${{props.criacao || '-'}}</span></div>
            <div class="popup-row"><span>Area Total:</span><span class="popup-val">${{areaHa}} ha</span></div>
            <div class="popup-row"><span>Taxa Media:</span><span class="popup-badge">${{taxaMedia}}% ao ano</span></div>
            <div class="popup-row"><span>Pico Historico:</span><span class="popup-val">${{taxaMax}}%</span></div>
            <div class="popup-row"><span>Queima Acumulada:</span><span class="popup-val">${{totalBurned}} ha</span></div>
          `;

          popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
        }}
      }});

      map.on('mouseleave', 'ucs-fill', () => {{
        map.getCanvas().style.cursor = '';
        map.setFilter('ucs-highlight', ['==', 'id', '']);
        popup.remove();
      }});

      // LOGICA DOS FILTROS INTERATIVOS
      const selGer = document.getElementById('select-gerencia');
      const selGrp = document.getElementById('select-grupo');
      const selBase = document.getElementById('select-basemap');

      function aplicarFiltros() {{
        const gerVal = selGer.value;
        const grpVal = selGrp.value;

        const filters = ['all'];

        if (gerVal !== 'TODAS') {{
          filters.push(['in', gerVal, ['get', 'gerencia']]);
        }}

        if (grpVal !== 'TODOS') {{
          filters.push(['==', ['get', 'grupo'], grpVal]);
        }}

        const filterExpr = filters.length > 1 ? filters : null;
        map.setFilter('ucs-fill', filterExpr);
        map.setFilter('ucs-line', filterExpr);

        // Atualizar estatisticas dos poligonos visiveis
        const featuresFiltradas = ucsData.features.filter(f => {{
          const p = f.properties;
          const matchGer = (gerVal === 'TODAS') || (p.gerencia && p.gerencia.includes(gerVal));
          const matchGrp = (grpVal === 'TODOS') || (p.grupo === grpVal);
          return matchGer && matchGrp;
        }});

        const totalUcs = featuresFiltradas.length;
        const totalArea = featuresFiltradas.reduce((acc, f) => acc + (f.properties.area_ha || 0), 0);
        const taxaMedia = totalUcs > 0
          ? (featuresFiltradas.reduce((acc, f) => acc + (f.properties.taxa_media_pct || 0), 0) / totalUcs)
          : 0.0;

        document.getElementById('stat-count').innerText = totalUcs;
        document.getElementById('stat-area').innerText = totalArea.toLocaleString('pt-BR', {{ maximumFractionDigits: 0 }}) + ' ha';
        document.getElementById('stat-taxa').innerText = taxaMedia.toFixed(2) + '% / ano';
      }}

      selGer.addEventListener('change', aplicarFiltros);
      selGrp.addEventListener('change', aplicarFiltros);

      selBase.addEventListener('change', (e) => {{
        if (e.target.value === 'sat') {{
          map.setLayoutProperty('basemap-gray', 'visibility', 'none');
          map.setLayoutProperty('basemap-sat', 'visibility', 'visible');
        }} else {{
          map.setLayoutProperty('basemap-sat', 'visibility', 'none');
          map.setLayoutProperty('basemap-gray', 'visibility', 'visible');
        }}
      }});
    }});
  </script>
</body>
</html>
"""

    if save_html:
        dest_html = output_path or (DATA_OUTPUT / "mapa_interativo_fogo_ucs.html")
        with open(dest_html, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"Mapa interativo MapLibre GL JS salvo em: {dest_html}")

    return html_template

def display_maplibre_in_notebook(df_series: pd.DataFrame, height: int = 650):
    """Gera e exibe o mapa interativo com filtros MapLibre GL JS diretamente no notebook."""
    from IPython.display import HTML
    import html as py_html

    html_raw = create_interactive_maplibre_map(df_series, save_html=True)
    escaped = py_html.escape(html_raw, quote=True)

    return HTML(f'''
    <div style="width: 100%; height: {height}px; border: 1px solid #CBD5E1; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.12);">
      <iframe srcdoc="{escaped}" style="width: 100%; height: 100%; border: none;" allow="fullscreen"></iframe>
    </div>
    ''')

"""
Modulo de cartografia e mapeamento espacial institucional.
Padronizado no layout cartografico oficial do NGEO/IDEFLOR-Bio (Prancha Paisagem A4/A3):
- Cabecalho superior com titulo oficial e bordas completas
- Painel cartografico principal (corpo esquerdo) com rotulos claros de Longitude e Latitude
- Coluna lateral direita:
  * Painel de Enquadramento Geografico / Localizacao no Brasil (com siglas e setas de chamada)
  * Painel de Legenda Tematica estruturada
  * Carimbo Institucional Oficial (NGEO / IDEFLOR-BIO)
- Mini Dashboard Interativo baseado em MapLibre GL JS com filtros por Gerencia Regional,
  Grupo SNUC, enquadramento dinamicamente ajustado e modulo deslizante de inspecao
  temporal com graficos interativos 1985 a 2023.
"""
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import folium
from folium import plugins
import branca.colormap as cm

from src.config import (
    GEOJSON_UCS,
    GEOJSON_PARA,
    GEOJSON_BRASIL_UFS_SIMP,
    GEOJSON_AMERICA_DO_SUL_SIMP,
    GEOJSON_BRASIL_UFS,
    GEOJSON_AMERICA_DO_SUL,
    CSV_METADATA_UCS,
    DATA_OUTPUT
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
    ano: Optional[int] = None,
    figsize: Tuple[int, int] = (16, 11),
    save_path: Optional[Path] = None
) -> Tuple[plt.Figure, Any]:
    """
    Gera prancha cartografica oficial no padrao institucional do NGEO / IDEFLOR-Bio:
    - Borda externa perimetral (neatline)
    - Todas as caixas delimitadoras com quatro bordas completas e visiveis (superior, inferior, esquerda, direita)
    - Painel principal esquerdo com rotulos limpos de Longitude e Latitude
    - Coluna lateral direita:
      * Painel superior: Enquadramento geografico focado no Brasil (com rotulos e setas de chamada)
      * Painel inferior: Legenda tematica estruturada e Carimbo Oficial do IDEFLOR-BIO
    """
    apply_ggplot_theme()
    plt.rcParams["savefig.bbox"] = None

    gdf_ucs = gpd.read_file(GEOJSON_UCS)
    gdf_para = gpd.read_file(GEOJSON_PARA)
    
    ufs_path = GEOJSON_BRASIL_UFS_SIMP if GEOJSON_BRASIL_UFS_SIMP.exists() else GEOJSON_BRASIL_UFS
    sa_path = GEOJSON_AMERICA_DO_SUL_SIMP if GEOJSON_AMERICA_DO_SUL_SIMP.exists() else GEOJSON_AMERICA_DO_SUL
    gdf_ufs = gpd.read_file(ufs_path)
    gdf_sa = gpd.read_file(sa_path)

    if ano is not None:
        df_sub = df_series[df_series["ano"] == ano].copy()
        uc_stats = df_sub[["uc_id", "taxa_queimada_pct", "burned_ha"]].rename(
            columns={"taxa_queimada_pct": "taxa_media_pct", "burned_ha": "burned_ha_total"}
        )
        subtitle = f"Distribuição Geográfica e Taxa Anual de Cicatrizes de Queimada - Ano {ano}"
        legenda_taxa = f"Taxa de Queima no Ano {ano} (% da UC):"
        tempo_info = f"Ano de Referência Analisado: {ano}"
    else:
        uc_stats = df_series.groupby("uc_id").agg(
            taxa_media_pct=("taxa_queimada_pct", "mean"),
            taxa_max_pct=("taxa_queimada_pct", "max"),
            burned_ha_total=("burned_ha", "sum")
        ).reset_index()
        subtitle = "Distribuição Geográfica e Taxa Média Histórica de Cicatrizes de Queimada (1985 a 2023)"
        legenda_taxa = "Taxa Média de Queima (% da UC / ano):"
        tempo_info = "Série Temporal Analisada: 1985 a 2023 (39 anos)"

    gdf_ucs = gdf_ucs.merge(uc_stats, left_on="id", right_on="uc_id", how="left")
    gdf_ucs["taxa_media_pct"] = gdf_ucs["taxa_media_pct"].fillna(0.0)

    fig = plt.figure(figsize=figsize, facecolor="#FFFFFF")

    # Moldura externa geral (neatline)
    neatline = patches.Rectangle(
        (0.022, 0.022), 0.956, 0.956,
        transform=fig.transFigure,
        fill=False, edgecolor="#000000", linewidth=1.5
    )
    fig.patches.append(neatline)

    # Coordenadas internas calibradas para folga perfeita dos rotulos e ausencia de cortes
    # Coordenadas internas com espacamento uniforme (gap = 0.015) e alinhamento milimetrico
    # ax_main e ax_inset perfeitamente alinhados no topo (0.880)
    # ax_main e ax_side perfeitamente alinhados na base (0.075)
    # ax_inset e ax_side com largura identica (0.240) e alinhados a direita (0.965)
    ax_head  = fig.add_axes([0.035, 0.895, 0.930, 0.065])
    ax_main  = fig.add_axes([0.085, 0.075, 0.625, 0.805])
    ax_inset = fig.add_axes([0.725, 0.525, 0.240, 0.355])
    ax_side  = fig.add_axes([0.725, 0.075, 0.240, 0.435])

    # Garantir expressamente a visibilidade de todas as quatro bordas em todos os quadrantes
    for ax in [ax_head, ax_main, ax_inset, ax_side]:
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color("#000000")
            spine.set_linewidth(1.3)

    # 1. CABECALHO SUPERIOR (TITULO DO MAPA)
    ax_head.set_facecolor("#FFFFFF")
    ax_head.set_xticks([])
    ax_head.set_yticks([])
    ax_head.text(
        0.5, 0.60,
        "UNIDADES DE CONSERVAÇÃO ESTADUAIS",
        fontsize=15.0, fontweight="bold", color="#000000", ha="center", va="center"
    )
    ax_head.text(
        0.5, 0.25,
        subtitle,
        fontsize=9.8, color="#334155", ha="center", va="center"
    )

    # 2. PAINEL PRINCIPAL (MAPA DO PARA E UCS)
    ax_main.set_facecolor("#E0F2FE")  # Oceano Atlantico
    xlim = (-59.2, -45.6)
    ylim = (-10.4, 3.2)
    ax_main.set_xlim(xlim)
    ax_main.set_ylim(ylim)

    gdf_sa.plot(ax=ax_main, facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.6, zorder=2)
    gdf_ufs.plot(ax=ax_main, facecolor="#F8FAFC", edgecolor="#D1D5DB", linewidth=0.6, zorder=3)
    gdf_para.plot(ax=ax_main, facecolor="#FFFFFF", edgecolor="#000000", linewidth=1.8, zorder=4)

    classes_cores = [
        {"min": 0.0, "max": 0.5, "cor": "#FFFFB2", "label": "0,00% a 0,50% (Baixíssima pressão)"},
        {"min": 0.5, "max": 2.0, "cor": "#FECC5C", "label": "0,51% a 2,00% (Baixa pressão)"},
        {"min": 2.0, "max": 4.0, "cor": "#FD8D3C", "label": "2,01% a 4,00% (Moderada pressão)"},
        {"min": 4.0, "max": 7.0, "cor": "#F03B20", "label": "4,01% a 7,00% (Alta pressão)"},
        {"min": 7.0, "max": 100.0, "cor": "#BD0026", "label": "Acima de 7,00% (Pressão crítica)"}
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

    rotulos_vizinhos = [
        {"texto": "AMAZONAS", "pos": (-58.2, -4.5)},
        {"texto": "MATO GROSSO", "pos": (-54.5, -9.9)},
        {"texto": "TOCANTINS", "pos": (-48.2, -6.8)},
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

    x_ticks = np.arange(-58, -44, 4)
    y_ticks = np.arange(-10, 4, 2)
    ax_main.set_xticks(x_ticks)
    ax_main.set_yticks(y_ticks)
    ax_main.set_xticklabels([f"{abs(int(x))}°0'0\"W" for x in x_ticks], fontsize=8, color="#000000")
    ax_main.set_yticklabels([f"{int(y)}°0'0\"N" if y > 0 else (f"{abs(int(y))}°0'0\"S" if y < 0 else "0°0'0\"") for y in y_ticks], fontsize=8, color="#000000")
    ax_main.grid(True, linestyle=":", color="#64748B", alpha=0.45, zorder=5)

    ax_main.set_xlabel("Longitude", fontsize=9.2, fontweight="bold", color="#334155", labelpad=7)
    ax_main.set_ylabel("Latitude", fontsize=9.2, fontweight="bold", color="#334155", labelpad=7)

    _draw_north_arrow(ax_main, x=-47.0, y=2.2, size=0.65)
    _draw_scale_bar(ax_main, x0=-49.0, y0=-9.3, length_km=300.0, lat_ref=-4.0)

    # 3. COLUNA DIREITA - PAINEL SUPERIOR: ENQUADRAMENTO GEOGRAFICO NO BRASIL
    ax_inset.set_facecolor("#E0F2FE")

    xlim_br = (-74.5, -30.0)
    ylim_br = (-34.0, 5.5)
    ax_inset.set_xlim(xlim_br)
    ax_inset.set_ylim(ylim_br)

    gdf_sa.plot(ax=ax_inset, facecolor="#F8FAFC", edgecolor="#E2E8F0", linewidth=0.3)
    gdf_ufs.plot(ax=ax_inset, facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.4)
    gdf_para.plot(ax=ax_inset, facecolor="#94A3B8", edgecolor="#475569", linewidth=0.8)

    # Retangulo delimitador da area de estudo em vermelho
    rect_extent = patches.Rectangle(
        (xlim[0], ylim[0]), xlim[1] - xlim[0], ylim[1] - ylim[0],
        linewidth=1.2, edgecolor="#DC2626", facecolor="none", linestyle="-", zorder=10
    )
    ax_inset.add_patch(rect_extent)

    # Rotulos diretos dos estados maiores sobre seus baricentros
    estados_diretos = [
        ("PA", -53.07, -3.98, "#FFFFFF", 8.5, "bold"),
        ("AM", -64.65, -4.15, "#64748B", 7.0, "normal"),
        ("RR", -61.39, 2.08, "#64748B", 6.5, "normal"),
        ("AP", -51.96, 1.45, "#64748B", 6.5, "normal"),
        ("AC", -70.47, -9.21, "#64748B", 6.5, "normal"),
        ("RO", -62.84, -10.91, "#64748B", 6.5, "normal"),
        ("MT", -55.91, -12.95, "#64748B", 7.0, "normal"),
        ("MS", -54.85, -20.33, "#64748B", 6.5, "normal"),
        ("TO", -48.33, -10.15, "#64748B", 6.5, "normal"),
        ("GO", -49.62, -16.04, "#64748B", 6.5, "normal"),
        ("MA", -45.29, -5.07, "#64748B", 6.5, "normal"),
        ("PI", -42.97, -7.39, "#64748B", 6.5, "normal"),
        ("CE", -39.62, -5.09, "#64748B", 6.5, "normal"),
        ("BA", -41.72, -12.48, "#64748B", 7.0, "normal"),
        ("MG", -44.67, -18.46, "#64748B", 7.0, "normal"),
        ("SP", -48.73, -22.27, "#64748B", 6.5, "normal"),
        ("PR", -51.62, -24.64, "#64748B", 6.5, "normal"),
        ("SC", -50.47, -27.25, "#64748B", 6.5, "normal"),
        ("RS", -53.24, -29.79, "#64748B", 6.5, "normal"),
    ]
    for sigla, x, y, cor, fsz, fweight in estados_diretos:
        ax_inset.text(x, y, sigla, fontsize=fsz, fontweight=fweight, color=cor, ha="center", va="center")

    # Setas de chamada (callouts) para estados costeiros menores
    estados_callouts = [
        ("RN", -36.67, -5.84, -32.5, -5.84),
        ("PB", -36.83, -7.12, -32.0, -7.12),
        ("PE", -38.00, -8.33, -32.5, -8.33),
        ("AL", -36.63, -9.51, -32.0, -9.51),
        ("SE", -37.44, -10.58, -32.5, -10.58),
        ("ES", -40.67, -19.57, -35.5, -19.57),
        ("RJ", -42.66, -22.20, -36.5, -22.20),
    ]
    for sigla, x_src, y_src, x_txt, y_txt in estados_callouts:
        ax_inset.annotate(
            sigla, xy=(x_src, y_src), xytext=(x_txt, y_txt),
            arrowprops=dict(arrowstyle="->", color="#64748B", lw=0.6),
            fontsize=6.5, fontweight="bold", color="#1E293B", va="center"
        )

    ax_inset.text(-50, 4.0, "Brasil", fontsize=9, fontweight="bold", color="#334155", ha="center")
    ax_inset.text(-36, -15, "Oceano\nAtlântico", fontsize=8, fontstyle="italic", color="#0284C7", ha="center")

    # Grade e rotulos de coordenadas do mapa de localizacao
    ax_inset.set_xlabel("")
    ax_inset.set_ylabel("")
    x_ticks_inset = [-70, -50, -30]
    y_ticks_inset = [-30, -15, 0]
    ax_inset.set_xticks(x_ticks_inset)
    ax_inset.set_yticks(y_ticks_inset)
    ax_inset.set_xticklabels([f"{abs(x)}°W" for x in x_ticks_inset], fontsize=6.5, color="#334155")
    ax_inset.set_yticklabels([f"{abs(y)}°S" if y < 0 else ("0°" if y == 0 else f"{y}°N") for y in y_ticks_inset], fontsize=6.5, color="#334155")
    ax_inset.tick_params(axis="both", which="both", labelsize=6.5, length=2.5, width=0.6, color="#475569", pad=2)
    ax_inset.grid(True, linestyle=":", color="#94A3B8", alpha=0.45, linewidth=0.5)

    # 4. COLUNA DIREITA - PAINEL INFERIOR: LEGENDA E CARIMBO INSTITUCIONAL
    ax_side.set_facecolor("#FFFFFF")
    ax_side.set_xticks([])
    ax_side.set_yticks([])

    ax_side.axhline(0.40, color="#000000", linewidth=1.2)

    # 4.1. SECAO DA LEGENDA
    ax_side.text(0.06, 0.94, "LEGENDA", fontsize=11, fontweight="bold", color="#000000", va="top")

    y_leg = 0.85
    rect_pa = patches.Rectangle((0.06, y_leg - 0.015), 0.08, 0.03, facecolor="#FFFFFF", edgecolor="#000000", linewidth=1.6)
    ax_side.add_patch(rect_pa)
    ax_side.text(0.18, y_leg, "Limite Estadual do Pará", fontsize=8.5, va="center", color="#000000")

    y_leg -= 0.065
    ax_side.text(0.06, y_leg, legenda_taxa, fontsize=8.8, fontweight="bold", color="#0F172A", va="center")

    for cl in classes_cores:
        y_leg -= 0.060
        box = patches.Rectangle((0.06, y_leg - 0.015), 0.08, 0.032, facecolor=cl["cor"], edgecolor="#000000", linewidth=0.8)
        ax_side.add_patch(box)
        ax_side.text(0.18, y_leg, cl["label"], fontsize=8.2, va="center", color="#000000")

    # 4.2. CARIMBO TECNICO / INSTITUCIONAL (RODAPE LATERAL)
    ax_side.text(0.06, 0.32, "Núcleo de Geotecnologias (NGEO)", fontsize=9.2, fontweight="bold", color="#000000")
    ax_side.text(0.06, 0.24, "Instituto de Desenvolvimento Florestal e da\nBiodiversidade do Estado do Pará - IDEFLOR-BIO", fontsize=7.8, fontweight="bold", color="#1E293B", linespacing=1.25)

    info_text = (
        "Base Territorial: 29 UCs Estaduais Oficiais\n"
        "Fonte do Regime de Fogo: MapBiomas Fogo (Coleção 3 - 30m)\n"
        f"{tempo_info}\n"
        "Sistema Geodésico: SIRGAS 2000 | Projeção Geográfica\n"
        "Data de Elaboração: Outubro de 2026"
    )
    ax_side.text(0.06, 0.04, info_text, fontsize=7.6, color="#334155", va="bottom", linespacing=1.35)

    if save_path:
        fig.savefig(save_path, dpi=300, facecolor="#FFFFFF")
        print(f"Prancha cartografica oficial salva com sucesso em: {save_path}")

    return fig, ax_main

def display_figure_responsive(fig, max_width_px: int = 1100, border: bool = True):
    """
    Exibe uma figura matplotlib de forma estavel e 100% responsiva no Google Colab
    e Jupyter Notebook, eliminando completamente trepidacao, oscilacao de scrollbars
    e conflitos de redimensionamento de iframe.
    """
    import io
    import base64
    from IPython.display import HTML, display
    import matplotlib.pyplot as plt

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    try:
        plt.close(fig)
    except Exception:
        pass
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode("utf-8")

    border_style = "border: 1px solid #CBD5E1; border-radius: 6px; box-shadow: 0 4px 14px rgba(0,0,0,0.08);" if border else ""
    html = f'''
    <div style="width: 100%; max-width: {max_width_px}px; margin: 8px auto; overflow: hidden; {border_style} background: #FFFFFF;">
      <img src="data:image/png;base64,{data}" alt="Visualizacao Grafica" style="width: 100%; height: auto; display: block;" />
    </div>
    '''
    display(HTML(html))

from src.viz.leaflet_dashboard import create_interactive_leaflet_dashboard

def create_interactive_maplibre_map(df_series: pd.DataFrame, save_html: bool = True, output_path: Optional[Path] = None) -> str:
    """Gera o Mini Dashboard analitico interativo (alias compativel com Colab e Jupyter)."""
    return create_interactive_leaflet_dashboard(df_series, save_html=save_html, output_path=output_path)

def display_maplibre_in_notebook(df_series: pd.DataFrame, height: int = 750):
    """
    Gera e exibe o Mini Dashboard analitico interativo diretamente no notebook.
    Utiliza iframe com srcdoc para compatibilidade total e imediata no Google Colab e VS Code,
    incluindo botao para abertura direta em nova aba do navegador.
    """
    from IPython.display import HTML
    import html as py_html
    import uuid

    html_raw = create_interactive_leaflet_dashboard(df_series, save_html=True)
    escaped = py_html.escape(html_raw, quote=True)
    uid = uuid.uuid4().hex[:8]
    iframe_id = f"dashboard_frame_{uid}"

    return HTML(f'''
    <div style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
      <span style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 12px; font-weight: 600; color: #475569;">
        Painel Espacial Interativo de Queimadas (IDEFLOR-Bio)
      </span>
      <a href="data/output/mapa_interativo_fogo_ucs.html" target="_blank"
         onclick="try {{ const w = window.open(); const doc = document.getElementById('{iframe_id}').getAttribute('srcdoc'); w.document.open(); w.document.write(doc); w.document.close(); return false; }} catch(e) {{ return true; }}"
         style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 12px; font-weight: 700; color: #1E3A8A; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; text-decoration: none; box-shadow: 0 1px 3px rgba(0,0,0,0.06); cursor: pointer; transition: all 0.2s ease;">
        <span>Abrir em Nova Aba</span>
        <span style="font-size: 14px;">↗</span>
      </a>
    </div>
    <div style="width: 100%; height: {height}px; border: 1px solid #CBD5E1; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.15); background: #0F172A;">
      <iframe id="{iframe_id}" srcdoc="{escaped}" style="width: 100%; height: 100%; border: none;" allow="fullscreen"></iframe>
    </div>
    ''')

def create_interactive_folium_map(
    df_series: pd.DataFrame,
    save_html: bool = True,
    output_path: Optional[Path] = None
) -> folium.Map:
    """
    Gera mapa interativo de alta compatibilidade e estabilidade nativa no Folium (Leaflet):
    - Camadas base gratuitas sem bloqueio de API key (Esri Canvas Claro, Esri Satélite, OpenStreetMap)
    - Limite Estadual do Pará destacado
    - Separação das 29 Unidades de Conservação por Gerências Regionais como camadas ativáveis/desativáveis
    - Estilização temática por classes de queima histórica
    - Tooltips completas com métricas consolidadas (área, taxa média, total queimado, criação)
    - Barra de escala cromática e controle de tela cheia
    """
    gdf_ucs = gpd.read_file(GEOJSON_UCS)
    gdf_para = gpd.read_file(GEOJSON_PARA)

    # Normalizar datas para evitar erros de serializacao json
    for col in gdf_ucs.columns:
        if pd.api.types.is_datetime64_any_dtype(gdf_ucs[col]):
            gdf_ucs[col] = gdf_ucs[col].astype(str)

    # Simplificacao suave para garantir alta responsividade em navegadores e no Google Colab
    gdf_ucs_simp = gdf_ucs.copy()
    gdf_ucs_simp["geometry"] = gdf_ucs_simp.geometry.simplify(0.002, preserve_topology=True)
    gdf_para_simp = gdf_para.copy()
    gdf_para_simp["geometry"] = gdf_para_simp.geometry.simplify(0.005, preserve_topology=True)

    # Consolidar estatisticas historicas por UC
    stats = df_series.groupby("uc_nome").agg(
        taxa_media=("taxa_queimada_pct", "mean"),
        burned_total=("burned_ha", "sum")
    ).reset_index().set_index("uc_nome").to_dict("index")

    gdf_ucs_simp["taxa_media"] = gdf_ucs_simp["name"].map(lambda x: round(stats.get(x, {}).get("taxa_media", 0.0), 2))
    gdf_ucs_simp["burned_total"] = gdf_ucs_simp["name"].map(lambda x: round(stats.get(x, {}).get("burned_total", 0.0), 1))

    # Inicializar mapa no centro geografico do Para
    m = folium.Map(location=[-3.8, -52.5], zoom_start=6, tiles=None)

    # 1. Esri Light Gray Canvas (gratuito e clean institucional)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, HERE, &copy; OpenStreetMap contributors",
        name="Mapa Base Claro (Esri Canvas)",
        control=True
    ).add_to(m)

    # 2. Esri World Imagery (satélite de alta resolução sem chave paga)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, Maxar, Earthstar Geographics",
        name="Satélite de Alta Resolução (Esri)",
        control=True
    ).add_to(m)

    # 3. OpenStreetMap oficial padrao
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="&copy; OpenStreetMap contributors",
        name="OpenStreetMap (Vias e Localidades)",
        control=True
    ).add_to(m)

    # Limite Estadual do Pará
    folium.GeoJson(
        gdf_para_simp,
        name="Limite Estadual do Pará",
        style_function=lambda x: {"fillColor": "transparent", "color": "#0F172A", "weight": 2, "dashArray": "4, 4"}
    ).add_to(m)

    def get_cor(t: float) -> str:
        if t <= 0.5:
            return "#FFFFB2"
        if t <= 2.0:
            return "#FECC5C"
        if t <= 4.0:
            return "#FD8D3C"
        if t <= 7.0:
            return "#F03B20"
        return "#BD0026"

    # Separação por Gerências Regionais como camadas ativáveis/desativáveis
    gerencias = sorted([g for g in gdf_ucs_simp["gerencia"].dropna().unique()])
    for ger in gerencias:
        subset = gdf_ucs_simp[gdf_ucs_simp["gerencia"] == ger]
        fg = folium.FeatureGroup(name=f"Gerência: {ger}", show=True)
        folium.GeoJson(
            subset,
            style_function=lambda f: {
                "fillColor": get_cor(f["properties"].get("taxa_media", 0)),
                "color": "#000000",
                "weight": 1.2,
                "fillOpacity": 0.85
            },
            highlight_function=lambda f: {"weight": 3.5, "color": "#000000", "fillOpacity": 1.0},
            tooltip=folium.GeoJsonTooltip(
                fields=["name", "gerencia", "categoria", "grupo", "criacao", "area_ha", "taxa_media", "burned_total"],
                aliases=["UC:", "Gerência Regional:", "Categoria:", "Grupo SNUC:", "Criação:", "Área (ha):", "Taxa Média/Ano (%):", "Total Queimado (ha):"],
                localize=True,
                sticky=True
            )
        ).add_to(fg)
        fg.add_to(m)

    # Escala de cores temática padronizada
    colormap = cm.StepColormap(
        colors=["#FFFFB2", "#FECC5C", "#FD8D3C", "#F03B20", "#BD0026"],
        index=[0.0, 0.5, 2.0, 4.0, 7.0, 15.0],
        vmin=0.0,
        vmax=15.0,
        caption="Taxa Média Histórica de Queima (% da UC / ano)"
    )
    colormap.add_to(m)

    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    plugins.Fullscreen(position="topright").add_to(m)

    if save_html:
        dest_html = output_path or (DATA_OUTPUT / "mapa_interativo_fogo_ucs.html")
        m.save(str(dest_html))
        print(f"Mapa interativo Folium salvo com sucesso em: {dest_html}")

    return m

"""
Modulo de cartografia e mapeamento espacial.
Gera prancha cartografica profissional em layout de atlas (GeoPandas e Matplotlib)
e mapa interativo vetorial baseado em MapLibre GL JS.
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

from src.config import (
    GEOJSON_UCS,
    GEOJSON_PARA,
    GEOJSON_BRASIL_UFS_SIMP,
    GEOJSON_AMERICA_DO_SUL_SIMP,
    GEOJSON_BRASIL_UFS,
    GEOJSON_AMERICA_DO_SUL,
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
    km_per_deg = 111.32 * np.cos(np.radians(lat_ref))
    length_deg = length_km / km_per_deg
    height_deg = 0.18

    half_deg = length_deg / 2.0
    half_km = length_km / 2.0

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

    rect1 = patches.Rectangle((x0, y0), half_deg, height_deg, facecolor="#1E293B", edgecolor="#1E293B", zorder=21)
    rect2 = patches.Rectangle((x0 + half_deg, y0), half_deg, height_deg, facecolor="#F8FAFC", edgecolor="#1E293B", zorder=21)
    ax.add_patch(rect1)
    ax.add_patch(rect2)

    ax.text(x0, y0 - 0.25, "0", ha="center", va="top", fontsize=7.5, color="#1E293B", fontweight="bold", zorder=22)
    ax.text(x0 + half_deg, y0 - 0.25, f"{int(half_km)}", ha="center", va="top", fontsize=7.5, color="#1E293B", fontweight="bold", zorder=22)
    ax.text(x0 + length_deg, y0 - 0.25, f"{int(length_km)} km", ha="center", va="top", fontsize=7.5, color="#1E293B", fontweight="bold", zorder=22)

def _draw_north_arrow(ax, x: float, y: float, size: float = 0.8):
    """Desenha indicador de norte cartografico minimalista."""
    circle = patches.Circle((x, y), size * 0.9, facecolor="#FFFFFF", edgecolor="#CBD5E1", linewidth=0.6, alpha=0.92, zorder=20)
    ax.add_patch(circle)

    poly_left = patches.Polygon([[x, y + size * 0.65], [x - size * 0.3, y - size * 0.4], [x, y]], facecolor="#0F172A", edgecolor="#0F172A", zorder=21)
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

    fig, ax = plt.subplots(figsize=figsize, facecolor="#F8FAFC")
    ax.set_facecolor("#E0F2FE")

    xlim = (-59.2, -45.6)
    ylim = (-10.4, 3.2)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    gdf_sa.plot(ax=ax, facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.7, zorder=2)
    gdf_ufs.plot(ax=ax, facecolor="#F8FAFC", edgecolor="#D1D5DB", linewidth=0.7, zorder=3)
    gdf_para.plot(ax=ax, facecolor="#FFFFFF", edgecolor="#334155", linewidth=1.6, zorder=4)

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

    x_ticks = np.arange(-58, -44, 4)
    y_ticks = np.arange(-10, 4, 2)
    ax.set_xticks(x_ticks)
    ax.set_yticks(y_ticks)
    ax.set_xticklabels([f"{abs(int(x))}°W" for x in x_ticks], fontsize=8.5, color=COLOR_TEXT_MUTED)
    ax.set_yticklabels([f"{int(y)}°N" if y > 0 else (f"{abs(int(y))}°S" if y < 0 else "0°") for y in y_ticks], fontsize=8.5, color=COLOR_TEXT_MUTED)
    ax.grid(True, linestyle=":", color="#94A3B8", alpha=0.5, zorder=5)

    _draw_scale_bar(ax, x0=-49.8, y0=-9.8, length_km=300.0, lat_ref=-4.0)
    _draw_north_arrow(ax, x=-46.8, y=1.9, size=0.65)

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

    gdf_sa.plot(ax=ax_inset, facecolor="#E2E8F0", edgecolor="#CBD5E1", linewidth=0.4)
    gdf_ufs.plot(ax=ax_inset, facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.3)
    gdf_para.plot(ax=ax_inset, facecolor="#D84315", edgecolor="#BF360C", linewidth=0.8)

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

def create_interactive_maplibre_map(
    df_series: pd.DataFrame,
    save_html: bool = True,
    output_path: Optional[Path] = None
) -> str:
    """
    Gera mapa vetorial interativo de alta performance utilizando MapLibre GL JS.
    Nao utiliza servidores com politicas de bloqueio (evita o erro do OpenStreetMap).
    Inclui controle de camadas, escala de cores termica e tooltips interativas.
    Retorna o codigo HTML completo como string.
    """
    with open(GEOJSON_UCS, "r", encoding="utf-8") as f:
        geo_ucs = json.load(f)

    with open(GEOJSON_PARA, "r", encoding="utf-8") as f:
        geo_para = json.load(f)

    # Inserir metricas agregadas nas propriedades dos poligonos
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
  <title>Mapa Interativo do Regime de Fogo nas UCs do Para (IDEFLOR-Bio)</title>
  
  <!-- MapLibre GL JS -->
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" />
  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>

  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body, html {{ width: 100%; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    #map {{ width: 100%; height: 100%; position: absolute; top: 0; bottom: 0; }}

    /* Painel Flutuante de Informacoes */
    .info-panel {{
      position: absolute;
      top: 16px;
      left: 16px;
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(8px);
      padding: 16px 20px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
      max-width: 380px;
      z-index: 10;
      border: 1px solid #E2E8F0;
    }}
    .info-panel h1 {{
      font-size: 15px;
      font-weight: 700;
      color: #0F172A;
      margin-bottom: 4px;
    }}
    .info-panel p {{
      font-size: 12px;
      color: #475569;
      line-height: 1.4;
    }}

    /* Legenda Tematica */
    .legend {{
      position: absolute;
      bottom: 24px;
      right: 16px;
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(8px);
      padding: 14px 18px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
      z-index: 10;
      border: 1px solid #E2E8F0;
      font-size: 11.5px;
      color: #1E293B;
    }}
    .legend-title {{
      font-weight: 700;
      margin-bottom: 8px;
      color: #0F172A;
    }}
    .legend-bar {{
      width: 220px;
      height: 12px;
      border-radius: 4px;
      background: linear-gradient(to right, #FFFFB2, #FECC5C, #FD8D3C, #F03B20, #BD0026);
      margin-bottom: 4px;
    }}
    .legend-labels {{
      display: flex;
      justify-content: space-between;
      font-size: 10px;
      color: #64748B;
      font-weight: 600;
    }}

    /* Tooltip Customizada */
    .maplibregl-popup-content {{
      padding: 14px 16px;
      border-radius: 8px;
      box-shadow: 0 6px 24px rgba(0,0,0,0.2);
      border: 1px solid #E2E8F0;
      font-size: 12px;
      max-width: 320px;
      line-height: 1.5;
    }}
    .popup-title {{
      font-size: 13.5px;
      font-weight: 700;
      color: #0F172A;
      margin-bottom: 6px;
      border-bottom: 1px solid #E2E8F0;
      padding-bottom: 4px;
    }}
    .popup-row {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 3px;
    }}
    .popup-label {{
      color: #64748B;
    }}
    .popup-value {{
      font-weight: 600;
      color: #0F172A;
    }}
    .popup-badge {{
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 700;
      background: #FEE2E2;
      color: #991B1B;
    }}
  </style>
</head>
<body>
  <div id="map"></div>

  <div class="info-panel">
    <h1>IDEFLOR-Bio | Sistema Estadual de UCs</h1>
    <p>Taxa Media Anual de Queima e Regime Historico de Fogo (1985 a 2023). Passe o cursor sobre os poligonos para inspecionar os indicadores.</p>
  </div>

  <div class="legend">
    <div class="legend-title">Taxa Media Anual de Queima (%/ano)</div>
    <div class="legend-bar"></div>
    <div class="legend-labels">
      <span>0.0%</span>
      <span>2.5%</span>
      <span>5.0%</span>
      <span>7.5%</span>
      <span>≥ 10.0%</span>
    </div>
  </div>

  <script>
    // Inicializacao do MapLibre GL JS com basemap vetorial confiavel (Carto Positron livre de bloqueios)
    const map = new maplibreGl.Map({{
      container: 'map',
      style: {{
        version: 8,
        sources: {{
          'carto-positron': {{
            type: 'raster',
            tiles: [
              'https://a.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png',
              'https://b.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png',
              'https://c.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png'
            ],
            tileSize: 256,
            attribution: '&copy; CartoDB &copy; OpenStreetMap contributors'
          }}
        }},
        layers: [
          {{
            id: 'carto-positron-layer',
            type: 'raster',
            source: 'carto-positron',
            minzoom: 0,
            maxzoom: 19
          }}
        ]
      }},
      center: [-52.5, -3.8],
      zoom: 5.6
    }});

    // Controles de Navegacao e Escala
    map.addControl(new maplibreGl.NavigationControl(), 'top-right');
    map.addControl(new maplibreGl.FullscreenControl(), 'top-right');
    map.addControl(new maplibreGl.ScaleControl({{ maxWidth: 120, unit: 'metric' }}), 'bottom-left');

    const ucsData = {geo_ucs_json_str};
    const paraData = {geo_para_json_str};

    map.on('load', () => {{
      // 1. Fonte e camada do Limite Estadual do Para
      map.addSource('limite-para', {{
        type: 'geojson',
        data: paraData
      }});

      map.addLayer({{
        id: 'limite-para-line',
        type: 'line',
        source: 'limite-para',
        paint: {{
          'line-color': '#334155',
          'line-width': 2.0,
          'line-dasharray': [3, 2]
        }}
      }});

      // 2. Fonte e camadas das 29 Unidades de Conservacao
      map.addSource('ucs-ideflor', {{
        type: 'geojson',
        data: ucsData
      }});

      // Preenchimento coropletico continuo baseado na taxa_media_pct
      map.addLayer({{
        id: 'ucs-fill',
        type: 'fill',
        source: 'ucs-ideflor',
        paint: {{
          'fill-color': [
            'interpolate',
            ['linear'],
            ['get', 'taxa_media_pct'],
            0.0, '#FFFFB2',
            1.5, '#FECC5C',
            3.5, '#FD8D3C',
            6.0, '#F03B20',
            10.0, '#BD0026'
          ],
          'fill-opacity': 0.82
        }}
      }});

      // Contorno das UCs
      map.addLayer({{
        id: 'ucs-line',
        type: 'line',
        source: 'ucs-ideflor',
        paint: {{
          'line-color': '#0F172A',
          'line-width': 1.0
        }}
      }});

      // Destaque (Hover)
      map.addLayer({{
        id: 'ucs-highlight',
        type: 'line',
        source: 'ucs-ideflor',
        paint: {{
          'line-color': '#000000',
          'line-width': 3.0
        }},
        filter: ['==', 'id', '']
      }});

      // Popup interativo
      const popup = new maplibreGl.Popup({{
        closeButton: false,
        closeOnClick: false
      }});

      map.on('mousemove', 'ucs-fill', (e) => {{
        map.getCanvas().style.cursor = 'pointer';

        if (e.features.length > 0) {{
          const feat = e.features[0];
          const props = feat.properties;

          map.setFilter('ucs-highlight', ['==', 'id', props.id]);

          const taxaMedia = Number(props.taxa_media_pct || 0).toFixed(2);
          const taxaMax = Number(props.taxa_max_pct || 0).toFixed(2);
          const areaHa = Number(props.area_ha || 0).toLocaleString('pt-BR', {{ maximumFractionDigits: 0 }});
          const totalBurned = Number(props.burned_ha_total || 0).toLocaleString('pt-BR', {{ maximumFractionDigits: 0 }});

          const html = `
            <div class="popup-title">${{props.name || props.nome_}}</div>
            <div class="popup-row"><span class="popup-label">Gerencia:</span><span class="popup-value">${{props.gerencia || '-'}}</span></div>
            <div class="popup-row"><span class="popup-label">Categoria:</span><span class="popup-value">${{props.categoria || '-'}} (${{props.grupo || '-'}})</span></div>
            <div class="popup-row"><span class="popup-label">Ano Criacao:</span><span class="popup-value">${{props.criacao || '-'}}</span></div>
            <div class="popup-row"><span class="popup-label">Area Total:</span><span class="popup-value">${{areaHa}} ha</span></div>
            <div class="popup-row"><span class="popup-label">Taxa Media:</span><span class="popup-badge">${{taxaMedia}}% ao ano</span></div>
            <div class="popup-row"><span class="popup-label">Pico Historico:</span><span class="popup-value">${{taxaMax}}%</span></div>
            <div class="popup-row"><span class="popup-label">Queima Total (1985-2023):</span><span class="popup-value">${{totalBurned}} ha</span></div>
          `;

          popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
        }}
      }});

      map.on('mouseleave', 'ucs-fill', () => {{
        map.getCanvas().style.cursor = '';
        map.setFilter('ucs-highlight', ['==', 'id', '']);
        popup.remove();
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
    """
    Gera e renderiza o mapa interativo MapLibre GL JS diretamente na celula do Jupyter Notebook.
    Utiliza srcdoc para garantir funcionamento compativel com JupyterLab, VS Code e Google Colab.
    """
    from IPython.display import HTML
    import html as py_html

    html_raw = create_interactive_maplibre_map(df_series, save_html=True)
    escaped = py_html.escape(html_raw, quote=True)

    return HTML(f'''
    <div style="width: 100%; height: {height}px; border: 1px solid #CBD5E1; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.12);">
      <iframe srcdoc="{escaped}" style="width: 100%; height: 100%; border: none;"></iframe>
    </div>
    ''')


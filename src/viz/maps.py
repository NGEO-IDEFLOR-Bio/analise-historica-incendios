"""
Modulo de cartografia e mapeamento espacial institucional.
Padronizado no layout cartografico oficial do NGEO/IDEFLOR-Bio (Prancha Paisagem A4/A3):
- Cabecalho superior com titulo oficial
- Painel cartografico principal (corpo esquerdo)
- Coluna lateral direita:
  * Painel de Enquadramento Geografico / Localizacao no Brasil (Para em destaque cinza)
  * Painel de Legenda Tematica estruturada
  * Carimbo Institucional (Metadados, Data, Projecao e Creditos)
- Mini Dashboard Interativo baseado em MapLibre GL JS com filtros por Gerencia Regional,
  Grupo SNUC, enquadramento otimizado de todas as feicoes e modulo deslizante de inspecao
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
    figsize: Tuple[int, int] = (16, 11),
    save_path: Optional[Path] = None
) -> Tuple[plt.Figure, Any]:
    """
    Gera prancha cartografica oficial no padrao institucional do NGEO / IDEFLOR-Bio:
    - Margens e moldura externa perimetral (neatline) com espacamento anti-corte
    - Cabecalho horizontal superior (titulo institucional completo)
    - Painel principal esquerdo (mapa tematico com grade, limites e UCs)
    - Coluna lateral direita:
      * Painel superior: Enquadramento geografico focado no Brasil (Para em cinza de destaque)
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

    uc_stats = df_series.groupby("uc_id").agg(
        taxa_media_pct=("taxa_queimada_pct", "mean"),
        taxa_max_pct=("taxa_queimada_pct", "max"),
        burned_ha_total=("burned_ha", "sum")
    ).reset_index()
    gdf_ucs = gdf_ucs.merge(uc_stats, left_on="id", right_on="uc_id", how="left")

    fig = plt.figure(figsize=figsize, facecolor="#FFFFFF")

    # Moldura externa geral (neatline) posicionada com margem livre em relacao a borda da folha
    neatline = patches.Rectangle(
        (0.025, 0.025), 0.950, 0.950,
        transform=fig.transFigure,
        fill=False, edgecolor="#000000", linewidth=1.5
    )
    fig.patches.append(neatline)

    # Coordenadas internas rigorosamente calibradas para eliminar sobreposicao e cortes
    ax_head = fig.add_axes([0.035, 0.895, 0.930, 0.065])
    ax_main = fig.add_axes([0.082, 0.075, 0.630, 0.805])
    ax_inset = fig.add_axes([0.730, 0.510, 0.235, 0.370])
    ax_side = fig.add_axes([0.730, 0.040, 0.235, 0.450])

    for ax in [ax_head, ax_main, ax_inset, ax_side]:
        for spine in ax.spines.values():
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
        "Distribuição Geográfica e Taxa Média Histórica de Cicatrizes de Queimada (1985 a 2023)",
        fontsize=9.8, color="#334155", ha="center", va="center"
    )

    # 2. PAINEL PRINCIPAL (MAPA DO PARA E UCS)
    ax_main.set_facecolor("#E0F2FE")  # Oceano Atlantico
    xlim = (-59.2, -45.6)
    ylim = (-10.4, 3.2)
    ax_main.set_xlim(xlim)
    ax_main.set_ylim(ylim)

    # Camadas de fundo
    gdf_sa.plot(ax=ax_main, facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.6, zorder=2)
    gdf_ufs.plot(ax=ax_main, facecolor="#F8FAFC", edgecolor="#D1D5DB", linewidth=0.6, zorder=3)
    gdf_para.plot(ax=ax_main, facecolor="#FFFFFF", edgecolor="#000000", linewidth=1.8, zorder=4)

    # Classes discretizadas de pressao do fogo
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

    # Grade de coordenadas com rotulos limpos de Longitude e Latitude
    x_ticks = np.arange(-58, -44, 4)
    y_ticks = np.arange(-10, 4, 2)
    ax_main.set_xticks(x_ticks)
    ax_main.set_yticks(y_ticks)
    ax_main.set_xticklabels([f"{abs(int(x))}°0'0\"W" for x in x_ticks], fontsize=8, color="#000000")
    ax_main.set_yticklabels([f"{int(y)}°0'0\"N" if y > 0 else (f"{abs(int(y))}°0'0\"S" if y < 0 else "0°0'0\"") for y in y_ticks], fontsize=8, color="#000000")
    ax_main.grid(True, linestyle=":", color="#64748B", alpha=0.45, zorder=5)

    ax_main.set_xlabel("Longitude", fontsize=9, fontweight="bold", color="#334155", labelpad=6)
    ax_main.set_ylabel("Latitude", fontsize=9, fontweight="bold", color="#334155", labelpad=6)

    # Rosa dos ventos e escala grafica no painel principal
    _draw_north_arrow(ax_main, x=-47.0, y=2.2, size=0.65)
    _draw_scale_bar(ax_main, x0=-57.8, y0=-9.2, length_km=300.0, lat_ref=-4.0)

    # 3. COLUNA DIREITA - PAINEL SUPERIOR: ENQUADRAMENTO GEOGRAFICO FOCADO NO BRASIL
    ax_inset.set_facecolor("#E0F2FE")

    xlim_br = (-74.5, -34.5)
    ylim_br = (-34.0, 5.5)
    ax_inset.set_xlim(xlim_br)
    ax_inset.set_ylim(ylim_br)

    gdf_sa.plot(ax=ax_inset, facecolor="#F8FAFC", edgecolor="#E2E8F0", linewidth=0.3)
    gdf_ufs.plot(ax=ax_inset, facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.4)
    # Estado do Para destacado em cinza institucional (nao preto)
    gdf_para.plot(ax=ax_inset, facecolor="#94A3B8", edgecolor="#475569", linewidth=0.8)

    rect_extent = patches.Rectangle(
        (xlim[0], ylim[0]), xlim[1] - xlim[0], ylim[1] - ylim[0],
        linewidth=1.2, edgecolor="#DC2626", facecolor="none", linestyle="-", zorder=10
    )
    ax_inset.add_patch(rect_extent)

    ax_inset.set_xticks([])
    ax_inset.set_yticks([])

    ax_inset.text(-50, 3.5, "Brasil", fontsize=9, fontweight="bold", color="#334155", ha="center")
    ax_inset.text(-38, -12, "Oceano\nAtlântico", fontsize=8, fontstyle="italic", color="#0284C7", ha="center")
    ax_inset.text(-52, -4, "PA", fontsize=9, fontweight="bold", color="#FFFFFF", ha="center")
    ax_inset.text(-63, -4, "AM", fontsize=7.5, color="#64748B")
    ax_inset.text(-53, -13, "MT", fontsize=7.5, color="#64748B")
    ax_inset.text(-48, -10, "TO", fontsize=7.5, color="#64748B")
    ax_inset.text(-45, -5, "MA", fontsize=7.5, color="#64748B")
    ax_inset.text(-51, 1.5, "AP", fontsize=7.5, color="#64748B")

    # 4. COLUNA DIREITA - PAINEL INFERIOR: LEGENDA E CARIMBO INSTITUCIONAL
    ax_side.set_facecolor("#FFFFFF")
    ax_side.set_xticks([])
    ax_side.set_yticks([])

    ax_side.axhline(0.38, color="#000000", linewidth=1.2)

    # 4.1. SECAO DA LEGENDA
    ax_side.text(0.06, 0.94, "LEGENDA", fontsize=11, fontweight="bold", color="#000000", va="top")

    y_leg = 0.85
    rect_pa = patches.Rectangle((0.06, y_leg - 0.015), 0.08, 0.03, facecolor="#FFFFFF", edgecolor="#000000", linewidth=1.6)
    ax_side.add_patch(rect_pa)
    ax_side.text(0.18, y_leg, "Limite Estadual do Pará", fontsize=8.5, va="center", color="#000000")

    y_leg -= 0.065
    ax_side.text(0.06, y_leg, "Taxa Média de Queima (% da UC / ano):", fontsize=8.8, fontweight="bold", color="#0F172A", va="center")

    for cl in classes_cores:
        y_leg -= 0.060
        box = patches.Rectangle((0.06, y_leg - 0.015), 0.08, 0.032, facecolor=cl["cor"], edgecolor="#000000", linewidth=0.8)
        ax_side.add_patch(box)
        ax_side.text(0.18, y_leg, cl["label"], fontsize=8.2, va="center", color="#000000")

    # 4.2. CARIMBO TECNICO / INSTITUCIONAL (RODAPE LATERAL)
    # Identificacao institucional oficial exigida pelo NGEO/IDEFLOR-Bio
    ax_side.text(0.06, 0.32, "Núcleo de Geotecnologias (NGEO)", fontsize=9.2, fontweight="bold", color="#000000")
    ax_side.text(0.06, 0.24, "Instituto de Desenvolvimento Florestal e da\nBiodiversidade do Estado do Pará - IDEFLOR-BIO", fontsize=7.8, fontweight="bold", color="#1E293B", linespacing=1.25)

    info_text = (
        "Base Territorial: 29 UCs Estaduais Oficiais\n"
        "Fonte do Regime de Fogo: MapBiomas Fogo (Coleção 3 - 30m)\n"
        "Série Temporal Analisada: 1985 a 2023 (39 anos)\n"
        "Sistema Geodésico: SIRGAS 2000 | Projeção Geográfica\n"
        "Data de Elaboração: Outubro de 2026"
    )
    ax_side.text(0.06, 0.04, info_text, fontsize=7.6, color="#334155", va="bottom", linespacing=1.35)

    if save_path:
        fig.savefig(save_path, dpi=300, facecolor="#FFFFFF")
        print(f"Prancha cartografica oficial salva com sucesso em: {save_path}")

    return fig, ax_main

def create_interactive_maplibre_map(
    df_series: pd.DataFrame,
    save_html: bool = True,
    output_path: Optional[Path] = None
) -> str:
    """
    Gera Mini Dashboard analitico interativo de alta performance com MapLibre GL JS:
    - Base vetorial otimizada 2D WGS84 (< 300 KB) com cores tematicas diretas
    - Enquadramento inicial perfeito com ajuste automatico de limites (fitBounds)
    - Painel lateral esquerdo compacto (250px) com recolhimento para visualizacao desobstruida
    - Modulo de inspecao analitica detalhada da UC selecionada que surge apenas sob demanda
    - Grafico Canvas anual (1985 a 2023) com tooltips e marco legal de criacao
    """
    df_meta = pd.read_csv(CSV_METADATA_UCS)
    gdf_ucs = gpd.read_file(GEOJSON_UCS)
    gdf_para = gpd.read_file(GEOJSON_PARA)

    gdf_ucs_simp = gdf_ucs.copy()
    gdf_ucs_simp["geometry"] = gdf_ucs_simp["geometry"].simplify(0.003, preserve_topology=True)
    gdf_para_simp = gdf_para.copy()
    gdf_para_simp["geometry"] = gdf_para_simp["geometry"].simplify(0.008, preserve_topology=True)

    series_by_uc = {}
    for uid, group in df_series.groupby("uc_id"):
        uid = int(uid)
        meta_row = df_meta[df_meta["id"] == uid]
        ano_criacao = int(meta_row["ano_criacao"].values[0]) if not meta_row.empty and not pd.isna(meta_row["ano_criacao"].values[0]) else None

        grp_sorted = group.sort_values("ano")
        anos = [int(a) for a in grp_sorted["ano"].tolist()]
        taxas = [round(float(v), 2) for v in grp_sorted["taxa_queimada_pct"].tolist()]
        burned_ha = [round(float(v), 1) for v in grp_sorted["burned_ha"].tolist()]

        if ano_criacao:
            pre_grp = grp_sorted[grp_sorted["ano"] < ano_criacao]
            pos_grp = grp_sorted[grp_sorted["ano"] >= ano_criacao]
            taxa_pre = round(float(pre_grp["taxa_queimada_pct"].mean()), 2) if not pre_grp.empty else None
            taxa_pos = round(float(pos_grp["taxa_queimada_pct"].mean()), 2) if not pos_grp.empty else None
        else:
            taxa_pre = None
            taxa_pos = None

        idx_max = grp_sorted["taxa_queimada_pct"].idxmax()
        row_max = grp_sorted.loc[idx_max]

        series_by_uc[uid] = {
            "anos": anos,
            "taxas": taxas,
            "ha": burned_ha,
            "taxa_pre": taxa_pre,
            "taxa_pos": taxa_pos,
            "pico_ano": int(row_max["ano"]),
            "pico_taxa": round(float(row_max["taxa_queimada_pct"]), 2),
            "burned_ha_total": round(float(grp_sorted["burned_ha"].sum()), 1),
            "taxa_media": round(float(grp_sorted["taxa_queimada_pct"].mean()), 2)
        }

    # Atribuicao de cor direta por classe para garantir 100% de compatibilidade WebGL
    def get_color(taxa: float) -> str:
        if taxa <= 0.50:
            return "#FFFFB2"
        elif taxa <= 2.00:
            return "#FECC5C"
        elif taxa <= 4.00:
            return "#FD8D3C"
        elif taxa <= 7.00:
            return "#F03B20"
        return "#BD0026"

    ucs_features = []
    for _, row in gdf_ucs_simp.iterrows():
        uid = int(row["id"])
        meta = df_meta[df_meta["id"] == uid]
        st = series_by_uc.get(uid, {})
        t_media = float(st.get("taxa_media", 0.0))

        geom_2d = json.loads(json.dumps(mapping(row["geometry"])))
        def strip_z(coords):
            if isinstance(coords[0], (int, float)):
                return [round(coords[0], 5), round(coords[1], 5)]
            return [strip_z(c) for c in coords]
        geom_2d["coordinates"] = strip_z(geom_2d["coordinates"])

        props = {
            "id": uid,
            "nome": meta["nome"].values[0] if not meta.empty else str(row.get("name", "")),
            "categoria": meta["categoria"].values[0] if not meta.empty else str(row.get("categoria", "")),
            "grupo": meta["grupo"].values[0] if not meta.empty else str(row.get("grupo", "")),
            "gerencia": meta["gerencia"].values[0] if not meta.empty else str(row.get("gerencia", "")),
            "criacao": int(meta["ano_criacao"].values[0]) if not meta.empty and not pd.isna(meta["ano_criacao"].values[0]) else None,
            "area_ha": float(meta["area_ha"].values[0]) if not meta.empty else float(row.get("area_ha", 0)),
            "taxa_media": t_media,
            "cor": get_color(t_media),
            "pico_ano": st.get("pico_ano", None),
            "pico_taxa": st.get("pico_taxa", 0.0),
            "taxa_pre": st.get("taxa_pre", None),
            "taxa_pos": st.get("taxa_pos", None),
            "burned_ha_total": st.get("burned_ha_total", 0.0)
        }
        ucs_features.append({
            "type": "Feature",
            "id": uid,
            "geometry": geom_2d,
            "properties": props
        })

    geo_ucs_clean = {"type": "FeatureCollection", "features": ucs_features}

    geom_para_2d = json.loads(json.dumps(mapping(gdf_para_simp.iloc[0]["geometry"])))
    def strip_z_para(coords):
        if isinstance(coords[0], (int, float)):
            return [round(coords[0], 5), round(coords[1], 5)]
        return [strip_z_para(c) for c in coords]
    geom_para_2d["coordinates"] = strip_z_para(geom_para_2d["coordinates"])

    geo_para_clean = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": geom_para_2d, "properties": {"name": "Pará"}}]
    }

    clean_ucs_str = json.dumps(geo_ucs_clean, ensure_ascii=False)
    clean_para_str = json.dumps(geo_para_clean, ensure_ascii=False)
    series_json_str = json.dumps(series_by_uc, ensure_ascii=False)

    html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Dashboard Analítico de Incêndios - UCs Estaduais do Pará</title>
  
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" />
  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>

  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ width: 100%; height: 100%; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0F172A; }}
    #map {{ width: 100%; height: 100%; position: absolute; top: 0; bottom: 0; left: 0; right: 0; }}

    /* Painel Esquerdo Compacto: Filtros e Totais */
    .left-panel {{
      position: absolute;
      top: 12px;
      left: 12px;
      width: 250px;
      background: rgba(255, 255, 255, 0.96);
      backdrop-filter: blur(8px);
      padding: 12px 14px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.22);
      border: 1px solid #CBD5E1;
      z-index: 10;
      transition: transform 0.25s ease;
      max-height: calc(100% - 24px);
      overflow-y: auto;
    }}
    .left-panel.collapsed {{
      transform: translateX(-275px);
    }}
    .panel-header-row {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 4px;
    }}
    .btn-panel-toggle {{
      background: #F1F5F9;
      border: 1px solid #CBD5E1;
      border-radius: 4px;
      padding: 2px 7px;
      font-size: 11px;
      font-weight: 700;
      color: #475569;
      cursor: pointer;
      line-height: 1.2;
    }}
    .btn-panel-toggle:hover {{
      background: #E2E8F0;
      color: #0F172A;
    }}
    .btn-expand-floating {{
      position: absolute;
      top: 12px;
      left: 12px;
      z-index: 11;
      background: #FFFFFF;
      border: 1px solid #CBD5E1;
      border-radius: 4px;
      padding: 6px 10px;
      font-size: 11px;
      font-weight: 700;
      color: #0F172A;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }}
    .btn-expand-floating:hover {{
      background: #F8FAFC;
    }}
    .panel-brand {{
      font-size: 12px;
      font-weight: 800;
      color: #0F172A;
      text-transform: uppercase;
      line-height: 1.2;
    }}
    .panel-subbrand {{
      font-size: 9.8px;
      font-weight: 600;
      color: #0284C7;
      margin-top: 2px;
      margin-bottom: 8px;
      border-bottom: 1px solid #E2E8F0;
      padding-bottom: 6px;
    }}
    .filter-group {{
      margin-bottom: 8px;
    }}
    .filter-label {{
      font-size: 10.5px;
      font-weight: 700;
      color: #334155;
      margin-bottom: 3px;
      display: block;
    }}
    .filter-select {{
      width: 100%;
      padding: 5px 6px;
      font-size: 11px;
      border: 1px solid #CBD5E1;
      border-radius: 4px;
      background: #FFFFFF;
      color: #0F172A;
    }}

    .kpi-container {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 5px;
      margin-top: 8px;
    }}
    .kpi-card {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 4px;
      padding: 6px 8px;
    }}
    .kpi-label {{
      font-size: 8.8px;
      color: #64748B;
      font-weight: 600;
      text-transform: uppercase;
    }}
    .kpi-value {{
      font-size: 12px;
      font-weight: 800;
      color: #0F172A;
      margin-top: 2px;
    }}

    /* Barra Superior de Orientacao */
    .hint-pill {{
      position: absolute;
      top: 12px;
      left: calc(260px + (100% - 260px) / 2);
      transform: translateX(-50%);
      background: rgba(15, 23, 42, 0.88);
      backdrop-filter: blur(6px);
      color: #FFFFFF;
      padding: 5px 14px;
      border-radius: 20px;
      font-size: 10.5px;
      font-weight: 600;
      z-index: 9;
      pointer-events: none;
      box-shadow: 0 2px 10px rgba(0,0,0,0.25);
      white-space: nowrap;
    }}

    /* Painel Direito Deslizante: Mini Dashboard da UC Selecionada */
    .right-inspector {{
      position: absolute;
      top: 12px;
      right: 12px;
      width: 360px;
      background: rgba(255, 255, 255, 0.98);
      backdrop-filter: blur(10px);
      padding: 14px 16px;
      border-radius: 8px;
      box-shadow: 0 4px 28px rgba(0,0,0,0.3);
      border: 1px solid #CBD5E1;
      z-index: 15;
      display: none;
      max-height: calc(100% - 24px);
      overflow-y: auto;
      animation: slideInRight 0.25s ease-out;
    }}
    @keyframes slideInRight {{
      from {{ transform: translateX(380px); opacity: 0; }}
      to {{ transform: translateX(0); opacity: 1; }}
    }}
    .inspector-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 6px;
    }}
    .uc-title {{
      font-size: 13.5px;
      font-weight: 800;
      color: #0F172A;
      line-height: 1.25;
    }}
    .btn-close {{
      background: #F1F5F9;
      border: 1px solid #CBD5E1;
      border-radius: 4px;
      width: 24px;
      height: 24px;
      cursor: pointer;
      font-weight: 700;
      font-size: 12px;
      color: #475569;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-left: 8px;
      flex-shrink: 0;
    }}
    .btn-close:hover {{
      background: #E2E8F0;
      color: #0F172A;
    }}
    .badge-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-bottom: 10px;
    }}
    .badge {{
      font-size: 9px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 3px;
      text-transform: uppercase;
      letter-spacing: 0.2px;
    }}
    .badge-gerencia {{ background: #E0F2FE; color: #0369A1; border: 1px solid #BAE6FD; }}
    .badge-grupo {{ background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }}
    .badge-cat {{ background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; }}

    /* Comparativo Pre vs Pos */
    .impact-box {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 8px 10px;
      margin-bottom: 10px;
    }}
    .impact-title {{
      font-size: 9.5px;
      font-weight: 700;
      text-transform: uppercase;
      color: #475569;
      margin-bottom: 5px;
    }}
    .impact-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 3px;
      font-size: 11px;
    }}
    .diff-badge {{
      font-size: 9.5px;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 3px;
    }}
    .diff-reduction {{ background: #DCFCE7; color: #166534; }}
    .diff-increase {{ background: #FEE2E2; color: #991B1B; }}

    /* Grafico Canvas */
    .chart-container {{
      margin-top: 8px;
      position: relative;
    }}
    .chart-title {{
      font-size: 10px;
      font-weight: 700;
      color: #334155;
      margin-bottom: 4px;
      display: flex;
      justify-content: space-between;
    }}
    #chart-canvas {{
      width: 100%;
      height: 150px;
      background: #FFFFFF;
      border: 1px solid #E2E8F0;
      border-radius: 4px;
      display: block;
    }}
    .chart-tooltip {{
      position: absolute;
      display: none;
      background: rgba(15, 23, 42, 0.94);
      color: #FFFFFF;
      padding: 4px 7px;
      border-radius: 4px;
      font-size: 9.5px;
      font-weight: 600;
      pointer-events: none;
      z-index: 30;
      white-space: nowrap;
    }}

    /* Legenda Cartografica */
    .legend {{
      position: absolute;
      bottom: 20px;
      left: 12px;
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(8px);
      padding: 8px 12px;
      border-radius: 6px;
      box-shadow: 0 4px 18px rgba(0,0,0,0.2);
      border: 1px solid #CBD5E1;
      font-size: 10px;
      z-index: 10;
    }}
    .legend-title {{
      font-weight: 700;
      color: #0F172A;
      margin-bottom: 5px;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      margin-bottom: 2px;
    }}
    .legend-box {{
      width: 13px;
      height: 9px;
      border: 1px solid #000;
      margin-right: 6px;
      border-radius: 2px;
    }}
  </style>
</head>
<body>
  <div id="map"></div>

  <!-- Indicador Superior -->
  <div class="hint-pill">Clique em qualquer Unidade de Conservação para inspecionar os indicadores históricos (1985–2023)</div>

  <!-- Botao Flutuante para reabrir painel quando recolhido -->
  <button id="btn-expand" class="btn-expand-floating" style="display: none;">&raquo; Filtros</button>

  <!-- Painel Esquerdo Compacto -->
  <div id="left-panel" class="left-panel">
    <div class="panel-header-row">
      <div>
        <div class="panel-brand">Painel Analítico de Incêndios</div>
        <div class="panel-subbrand">IDEFLOR-Bio | Núcleo de Geotecnologias</div>
      </div>
      <button id="btn-collapse" class="btn-panel-toggle" title="Recolher painel de filtros">&laquo;</button>
    </div>

    <div class="filter-group">
      <label class="filter-label" for="select-gerencia">Gerência Regional:</label>
      <select id="select-gerencia" class="filter-select">
        <option value="TODAS">Todas as Gerências (29 UCs)</option>
        <option value="GRCN-I">Calha Norte I (GRCN-I)</option>
        <option value="GRCN-II">Calha Norte II (GRCN-II)</option>
        <option value="GRCN-III">Calha Norte III (GRCN-III)</option>
        <option value="GRB">Belém (GRB)</option>
        <option value="GRTUC">Tucuruí (GRTUC)</option>
        <option value="GRA">Araguaia (GRA)</option>
        <option value="GRM">Marajó (GRM)</option>
        <option value="GRNE">Nordeste (GRNE)</option>
        <option value="GRX">Xingu (GRX)</option>
      </select>
    </div>

    <div class="filter-group">
      <label class="filter-label" for="select-grupo">Grupo SNUC:</label>
      <select id="select-grupo" class="filter-select">
        <option value="TODOS">Todos os Grupos</option>
        <option value="Proteção Integral">Proteção Integral</option>
        <option value="Uso Sustentável">Uso Sustentável</option>
      </select>
    </div>

    <div class="filter-group">
      <label class="filter-label" for="select-basemap">Camada de Fundo:</label>
      <select id="select-basemap" class="filter-select">
        <option value="gray">Esri World Gray (Cartográfico)</option>
        <option value="sat">Esri World Imagery (Satélite)</option>
      </select>
    </div>

    <div class="filter-group">
      <label class="filter-label" for="select-uc-direct">Selecionar UC Direta:</label>
      <select id="select-uc-direct" class="filter-select">
        <option value="">Selecione na lista...</option>
      </select>
    </div>

    <div class="kpi-container">
      <div class="kpi-card">
        <div class="kpi-label">UCs Filtradas</div>
        <div id="kpi-count" class="kpi-value">29</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Taxa Média</div>
        <div id="kpi-taxa" class="kpi-value" style="color: #EA580C;">1,72%</div>
      </div>
      <div class="kpi-card" style="grid-column: span 2;">
        <div class="kpi-label">Área Protegida Total</div>
        <div id="kpi-area" class="kpi-value">19.950.698 ha</div>
      </div>
    </div>
  </div>

  <!-- Painel Direito: Mini Dashboard Detalhado (Abre apenas sob clique) -->
  <div id="inspector" class="right-inspector">
    <div class="inspector-header">
      <div id="uc-name" class="uc-title">Nome da UC</div>
      <button id="btn-close-inspect" class="btn-close" title="Fechar Detalhes">&times;</button>
    </div>

    <div class="badge-bar">
      <span id="badge-cat" class="badge badge-cat">Categoria</span>
      <span id="badge-ger" class="badge badge-gerencia">Gerência</span>
      <span id="badge-grp" class="badge badge-grupo">Grupo</span>
    </div>

    <div class="kpi-container" style="margin-bottom: 10px;">
      <div class="kpi-card">
        <div class="kpi-label">Área Oficial</div>
        <div id="uc-area" class="kpi-value">0 ha</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Ano Criação</div>
        <div id="uc-criacao" class="kpi-value">-</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Taxa Média Anual</div>
        <div id="uc-taxa-media" class="kpi-value" style="color: #EA580C;">0,00%</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Pico Histórico</div>
        <div id="uc-pico" class="kpi-value">0,00%</div>
      </div>
    </div>

    <div class="impact-box">
      <div class="impact-title">Marco Temporal de Criação Legal</div>
      <div class="impact-row">
        <span>Média Pré-Criação:</span>
        <strong id="val-pre">-</strong>
      </div>
      <div class="impact-row">
        <span>Média Pós-Criação:</span>
        <strong id="val-pos">-</strong>
      </div>
      <div class="impact-row" style="margin-top: 3px; padding-top: 3px; border-top: 1px dashed #CBD5E1;">
        <span>Variação Observada:</span>
        <span id="badge-diff" class="diff-badge">-</span>
      </div>
    </div>

    <div class="chart-container">
      <div class="chart-title">
        <span>Evolução Anual da Taxa (% da UC)</span>
        <span style="font-size: 8.5px; color: #64748B;">1985–2023</span>
      </div>
      <canvas id="chart-canvas" width="326" height="150"></canvas>
      <div id="chart-tooltip" class="chart-tooltip"></div>
    </div>
  </div>

  <!-- Legenda Cartografica -->
  <div class="legend">
    <div class="legend-title">Taxa Média Anual de Queima</div>
    <div class="legend-item"><div class="legend-box" style="background: #FFFFB2;"></div><span>0,00% a 0,50% (Baixíssima)</span></div>
    <div class="legend-item"><div class="legend-box" style="background: #FECC5C;"></div><span>0,51% a 2,00% (Baixa)</span></div>
    <div class="legend-item"><div class="legend-box" style="background: #FD8D3C;"></div><span>2,01% a 4,00% (Moderada)</span></div>
    <div class="legend-item"><div class="legend-box" style="background: #F03B20;"></div><span>4,01% a 7,00% (Alta)</span></div>
    <div class="legend-item"><div class="legend-box" style="background: #BD0026;"></div><span>Acima de 7,00% (Crítica)</span></div>
  </div>

  <script>
    const ucsGeo = {clean_ucs_str};
    const paraGeo = {clean_para_str};
    const seriesData = {series_json_str};

    const selDirect = document.getElementById('select-uc-direct');
    ucsGeo.features
      .slice()
      .sort((a, b) => a.properties.nome.localeCompare(b.properties.nome))
      .forEach(f => {{
        const opt = document.createElement('option');
        opt.value = f.properties.id;
        opt.textContent = f.properties.nome;
        selDirect.appendChild(opt);
      }});

    const map = new maplibregl.Map({{
      container: 'map',
      style: {{
        version: 8,
        sources: {{
          'esri-gray': {{
            type: 'raster',
            tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}'],
            tileSize: 256,
            attribution: 'Esri, HERE, &copy; OpenStreetMap'
          }},
          'esri-sat': {{
            type: 'raster',
            tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}'],
            tileSize: 256,
            attribution: 'Esri, Maxar'
          }}
        }},
        layers: [
          {{ id: 'basemap-gray', type: 'raster', source: 'esri-gray', layout: {{ visibility: 'visible' }} }},
          {{ id: 'basemap-sat', type: 'raster', source: 'esri-sat', layout: {{ visibility: 'none' }} }}
        ]
      }},
      bounds: [[-58.8, -9.9], [-46.0, 2.5]],
      fitBoundsOptions: {{ padding: {{ top: 40, bottom: 40, left: 280, right: 40 }} }}
    }});

    // Garantir redimensionamento continuo
    const resizeHandler = () => {{
      map.resize();
    }};
    window.addEventListener('resize', resizeHandler);
    if (window.ResizeObserver) {{
      new ResizeObserver(resizeHandler).observe(document.getElementById('map'));
    }}
    setTimeout(resizeHandler, 250);
    setTimeout(resizeHandler, 750);
    setTimeout(resizeHandler, 1500);

    map.addControl(new maplibregl.NavigationControl(), 'bottom-right');
    map.addControl(new maplibregl.FullscreenControl(), 'bottom-right');

    // Alternar painel de filtros
    const leftPanel = document.getElementById('left-panel');
    const btnCollapse = document.getElementById('btn-collapse');
    const btnExpand = document.getElementById('btn-expand');

    btnCollapse.addEventListener('click', () => {{
      leftPanel.classList.add('collapsed');
      btnExpand.style.display = 'block';
      setTimeout(resizeHandler, 260);
    }});

    btnExpand.addEventListener('click', () => {{
      leftPanel.classList.remove('collapsed');
      btnExpand.style.display = 'none';
      setTimeout(resizeHandler, 260);
    }});

    function setupLayers() {{
      if (map.getSource('para-border')) return;

      map.addSource('para-border', {{
        type: 'geojson',
        data: paraGeo
      }});

      map.addLayer({{
        id: 'para-line',
        type: 'line',
        source: 'para-border',
        paint: {{
          'line-color': '#0F172A',
          'line-width': 1.8,
          'line-dasharray': [3, 2]
        }}
      }});

      map.addSource('ucs-ideflor', {{
        type: 'geojson',
        data: ucsGeo
      }});

      // Preenchimento com cor direta atribuida no GeoJSON
      map.addLayer({{
        id: 'ucs-fill',
        type: 'fill',
        source: 'ucs-ideflor',
        paint: {{
          'fill-color': ['get', 'cor'],
          'fill-opacity': 0.88
        }}
      }});

      map.addLayer({{
        id: 'ucs-line',
        type: 'line',
        source: 'ucs-ideflor',
        paint: {{
          'line-color': '#000000',
          'line-width': 0.9
        }}
      }});

      map.addLayer({{
        id: 'ucs-highlight',
        type: 'line',
        source: 'ucs-ideflor',
        paint: {{
          'line-color': '#000000',
          'line-width': 3.5
        }},
        filter: ['==', ['get', 'id'], -1]
      }});

      // Popup flutuante simples no hover
      const hoverPopup = new maplibregl.Popup({{
        closeButton: false,
        closeOnClick: false,
        offset: 12
      }});

      map.on('mousemove', 'ucs-fill', (e) => {{
        map.getCanvas().style.cursor = 'pointer';
        if (e.features && e.features.length > 0) {{
          const p = e.features[0].properties;
          hoverPopup
            .setLngLat(e.lngLat)
            .setHTML(`<strong>${{p.nome}}</strong><br/><span style="color:#64748B;">Gerência: ${{p.gerencia}} | Média: ${{Number(p.taxa_media).toFixed(2)}}%</span>`)
            .addTo(map);
        }}
      }});

      map.on('mouseleave', 'ucs-fill', () => {{
        map.getCanvas().style.cursor = '';
        hoverPopup.remove();
      }});

      map.on('click', 'ucs-fill', (e) => {{
        if (e.features && e.features.length > 0) {{
          const props = e.features[0].properties;
          selectUC(props.id);
        }}
      }});

      selDirect.addEventListener('change', (e) => {{
        if (e.target.value) {{
          selectUC(parseInt(e.target.value));
        }}
      }});

      document.getElementById('btn-close-inspect').addEventListener('click', () => {{
        clearSelection();
      }});

      // Filtros
      const selGer = document.getElementById('select-gerencia');
      const selGrp = document.getElementById('select-grupo');
      const selBase = document.getElementById('select-basemap');

      function updateFilters() {{
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

        const filtered = ucsGeo.features.filter(f => {{
          const p = f.properties;
          const matchGer = (gerVal === 'TODAS') || (p.gerencia && p.gerencia.includes(gerVal));
          const matchGrp = (grpVal === 'TODOS') || (p.grupo === grpVal);
          return matchGer && matchGrp;
        }});

        const count = filtered.length;
        const totalArea = filtered.reduce((acc, f) => acc + (f.properties.area_ha || 0), 0);
        const taxaMedia = count > 0
          ? (filtered.reduce((acc, f) => acc + (f.properties.taxa_media || 0), 0) / count)
          : 0.0;

        document.getElementById('kpi-count').innerText = count;
        document.getElementById('kpi-area').innerText = totalArea.toLocaleString('pt-BR', {{ maximumFractionDigits: 0 }}) + ' ha';
        document.getElementById('kpi-taxa').innerText = taxaMedia.toFixed(2) + '%';
      }}

      selGer.addEventListener('change', updateFilters);
      selGrp.addEventListener('change', updateFilters);

      selBase.addEventListener('change', (e) => {{
        if (e.target.value === 'sat') {{
          map.setLayoutProperty('basemap-gray', 'visibility', 'none');
          map.setLayoutProperty('basemap-sat', 'visibility', 'visible');
        }} else {{
          map.setLayoutProperty('basemap-sat', 'visibility', 'none');
          map.setLayoutProperty('basemap-gray', 'visibility', 'visible');
        }}
      }});
    }}

    map.on('load', setupLayers);
    if (map.isStyleLoaded()) setupLayers();

    function selectUC(id) {{
      map.setFilter('ucs-highlight', ['==', ['get', 'id'], id]);

      const feat = ucsGeo.features.find(f => f.properties.id === id);
      if (!feat) return;
      const p = feat.properties;
      const s = seriesData[id] || {{}};

      const inspector = document.getElementById('inspector');
      inspector.style.display = 'block';

      document.getElementById('uc-name').innerText = p.nome;
      document.getElementById('badge-cat').innerText = p.categoria || 'UC';
      document.getElementById('badge-ger').innerText = p.gerencia || '-';
      document.getElementById('badge-grp').innerText = p.grupo || '-';

      document.getElementById('uc-area').innerText = Number(p.area_ha).toLocaleString('pt-BR', {{ maximumFractionDigits: 0 }}) + ' ha';
      document.getElementById('uc-criacao').innerText = p.criacao ? p.criacao : 'Sem data';
      document.getElementById('uc-taxa-media').innerText = Number(p.taxa_media).toFixed(2) + '% / ano';
      document.getElementById('uc-pico').innerText = (p.pico_taxa ? p.pico_taxa.toFixed(2) + '% (' + p.pico_ano + ')' : '-');

      if (p.taxa_pre !== null && p.taxa_pos !== null) {{
        document.getElementById('val-pre').innerText = p.taxa_pre.toFixed(2) + '% / ano';
        document.getElementById('val-pos').innerText = p.taxa_pos.toFixed(2) + '% / ano';

        const diff = p.taxa_pos - p.taxa_pre;
        const diffPct = p.taxa_pre > 0 ? ((diff / p.taxa_pre) * 100).toFixed(1) : '0';
        const badgeDiff = document.getElementById('badge-diff');
        if (diff < 0) {{
          badgeDiff.className = 'diff-badge diff-reduction';
          badgeDiff.innerText = diffPct + '% (Redução da Queima)';
        }} else {{
          badgeDiff.className = 'diff-badge diff-increase';
          badgeDiff.innerText = '+' + diffPct + '% (Aumento da Queima)';
        }}
      }} else {{
        document.getElementById('val-pre').innerText = 'N/A';
        document.getElementById('val-pos').innerText = 'N/A';
        const badgeDiff = document.getElementById('badge-diff');
        badgeDiff.className = 'diff-badge';
        badgeDiff.innerText = 'Sem marco temporal pré/pós';
      }}

      renderChart(s, p.criacao);
    }}

    function clearSelection() {{
      map.setFilter('ucs-highlight', ['==', ['get', 'id'], -1]);
      document.getElementById('inspector').style.display = 'none';
      selDirect.value = '';
    }}

    function renderChart(series, anoCriacao) {{
      const canvas = document.getElementById('chart-canvas');
      const ctx = canvas.getContext('2d');
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);

      if (!series || !series.anos || series.anos.length === 0) return;

      const anos = series.anos;
      const taxas = series.taxas;
      const has = series.ha;
      const n = anos.length;
      const maxTaxa = Math.max(...taxas, 1.0);

      const paddingLeft = 30;
      const paddingRight = 8;
      const paddingTop = 14;
      const paddingBottom = 20;

      const plotW = width - paddingLeft - paddingRight;
      const plotH = height - paddingTop - paddingBottom;

      ctx.strokeStyle = '#E2E8F0';
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let i = 0; i <= 3; i++) {{
        const yVal = (maxTaxa * i) / 3;
        const yPos = paddingTop + plotH - (plotH * i) / 3;
        ctx.moveTo(paddingLeft, yPos);
        ctx.lineTo(width - paddingRight, yPos);
        ctx.fillStyle = '#64748B';
        ctx.font = '8px sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(yVal.toFixed(1) + '%', paddingLeft - 4, yPos + 3);
      }}
      ctx.stroke();

      const barW = (plotW / n) * 0.75;
      const step = plotW / n;

      for (let i = 0; i < n; i++) {{
        const ano = anos[i];
        const val = taxas[i];
        const barH = (val / maxTaxa) * plotH;
        const xPos = paddingLeft + i * step + (step - barW) / 2;
        const yPos = paddingTop + plotH - barH;

        if (anoCriacao && ano < anoCriacao) {{
          ctx.fillStyle = '#94A3B8';
        }} else {{
          ctx.fillStyle = '#EA580C';
        }}

        if (val === series.pico_taxa) {{
          ctx.fillStyle = '#B91C1C';
        }}

        ctx.fillRect(xPos, yPos, barW, barH);

        if (i === 0 || i === n - 1 || ano === anoCriacao) {{
          ctx.fillStyle = '#475569';
          ctx.font = '7.5px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(ano, xPos + barW / 2, height - 5);
        }}
      }}

      if (anoCriacao) {{
        const idx = anos.indexOf(anoCriacao);
        if (idx >= 0) {{
          const xMark = paddingLeft + idx * step + step / 2;
          ctx.setLineDash([3, 2]);
          ctx.strokeStyle = '#0284C7';
          ctx.lineWidth = 1.4;
          ctx.beginPath();
          ctx.moveTo(xMark, paddingTop);
          ctx.lineTo(xMark, paddingTop + plotH);
          ctx.stroke();
          ctx.setLineDash([]);

          ctx.fillStyle = '#0284C7';
          ctx.font = 'bold 7.5px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText('Criação', xMark, paddingTop - 4);
        }}
      }}

      canvas.onmousemove = (e) => {{
        const rect = canvas.getBoundingClientRect();
        const mouseX = (e.clientX - rect.left) * (canvas.width / rect.width);
        if (mouseX >= paddingLeft && mouseX <= width - paddingRight) {{
          const i = Math.floor((mouseX - paddingLeft) / step);
          if (i >= 0 && i < n) {{
            const ano = anos[i];
            const val = taxas[i];
            const ha = has[i];
            const tt = document.getElementById('chart-tooltip');
            tt.style.display = 'block';
            tt.style.left = (e.clientX - rect.left - 30) + 'px';
            tt.style.top = (e.clientY - rect.top - 28) + 'px';
            tt.innerHTML = `<strong>${{ano}}</strong>: ${{val.toFixed(2)}}% (${{ha.toLocaleString('pt-BR')}} ha)`;
          }}
        }}
      }};
      canvas.onmouseleave = () => {{
        document.getElementById('chart-tooltip').style.display = 'none';
      }};
    }}
  </script>
</body>
</html>
"""

    if save_html:
        dest_html = output_path or (DATA_OUTPUT / "mapa_interativo_fogo_ucs.html")
        with open(dest_html, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"Mini Dashboard MapLibre GL JS salvo em: {dest_html}")

    return html_template

def display_maplibre_in_notebook(df_series: pd.DataFrame, height: int = 700):
    """Gera e exibe o dashboard interativo MapLibre GL JS diretamente no notebook."""
    from IPython.display import HTML
    import html as py_html

    html_raw = create_interactive_maplibre_map(df_series, save_html=True)
    escaped = py_html.escape(html_raw, quote=True)

    return HTML(f'''
    <div style="width: 100%; height: {height}px; border: 1px solid #CBD5E1; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.15);">
      <iframe srcdoc="{escaped}" style="width: 100%; height: 100%; border: none;" allow="fullscreen"></iframe>
    </div>
    ''')

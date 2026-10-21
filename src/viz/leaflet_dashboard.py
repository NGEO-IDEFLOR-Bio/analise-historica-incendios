"""
Modulo gerador do Mini Dashboard Analitico Interativo em Leaflet + Chart.js.
Padronizacao institucional IDEFLOR-Bio:
- Painel analitico unificado com alternador de abas (Visao Regional vs Analise por Unidade)
- Zero conflito cognitivo entre filtros regionais e inspecao individual
- Zoom e enquadramento sincronizados dinamicamente a cada selecao
- Visualizacao grafica dual em Chart.js:
  * Visao Regional: Linha historica ponderada do grupo/gerencia filtrada
  * Analise por Unidade: Grafico temporal com marco legal do decreto (pre vs pos-criacao)
- Cartografia base profissional e gratuita: Esri Canvas Claro e Satelite
- 100% compativel com navegadores locais, VS Code e Google Colab (sem chave de API)
"""
from typing import Optional
from pathlib import Path
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping

from src.config import (
    GEOJSON_UCS,
    GEOJSON_PARA,
    CSV_METADATA_UCS,
    DATA_OUTPUT
)

def strip_z(coords):
    """Remove a dimensao Z (elevacao) de coordenadas para garantir compatibilidade GeoJSON 2D padrao."""
    if isinstance(coords[0], (int, float)):
        return coords[:2]
    return [strip_z(c) for c in coords]

def create_interactive_leaflet_dashboard(
    df_series: pd.DataFrame,
    save_html: bool = True,
    output_path: Optional[Path] = None
) -> str:
    gdf_ucs = gpd.read_file(GEOJSON_UCS)
    gdf_para = gpd.read_file(GEOJSON_PARA)
    df_meta = pd.read_csv(CSV_METADATA_UCS) if CSV_METADATA_UCS.exists() else pd.DataFrame()

    for col in gdf_ucs.columns:
        if pd.api.types.is_datetime64_any_dtype(gdf_ucs[col]):
            gdf_ucs[col] = gdf_ucs[col].astype(str)

    gdf_ucs_simp = gdf_ucs.copy()
    gdf_ucs_simp["geometry"] = gdf_ucs_simp.geometry.simplify(0.002, preserve_topology=True)
    gdf_para_simp = gdf_para.copy()
    gdf_para_simp["geometry"] = gdf_para_simp.geometry.simplify(0.005, preserve_topology=True)

    stats = df_series.groupby("uc_id").agg(
        taxa_media=("taxa_queimada_pct", "mean"),
        burned_ha_total=("burned_ha", "sum")
    ).to_dict("index")

    def get_cor(taxa: float) -> str:
        if taxa < 0.5:
            return "#FFFFB2"
        elif taxa < 2.0:
            return "#FECC5C"
        elif taxa < 4.0:
            return "#FD8D3C"
        elif taxa < 7.0:
            return "#F03B20"
        else:
            return "#BD0026"

    ucs_features = []
    for _, row in gdf_ucs_simp.iterrows():
        uid = int(row["id"])
        st = stats.get(uid, {"taxa_media": 0.0, "burned_ha_total": 0.0})
        meta_row = df_meta[df_meta["id"] == uid]
        nome_oficial = meta_row["nome"].values[0] if not meta_row.empty else str(row["name"])
        cat = meta_row["categoria"].values[0] if not meta_row.empty else str(row.get("categoria", ""))
        grp = meta_row["grupo"].values[0] if not meta_row.empty else str(row.get("grupo", ""))
        ger = meta_row["gerencia"].values[0] if not meta_row.empty else str(row.get("gerencia", ""))
        
        ger_sigla = ""
        if "(" in ger and ")" in ger:
            ger_sigla = ger.split("(")[-1].replace(")", "").strip()
            
        criacao = int(meta_row["ano_criacao"].values[0]) if not meta_row.empty and not pd.isna(meta_row["ano_criacao"].values[0]) else None
        
        geom_2d = json.loads(json.dumps(mapping(row["geometry"])))
        geom_2d["coordinates"] = strip_z(geom_2d["coordinates"])
        
        ucs_features.append({
            "type": "Feature",
            "id": uid,
            "geometry": geom_2d,
            "properties": {
                "id": uid,
                "nome": nome_oficial,
                "categoria": cat,
                "grupo": grp,
                "gerencia": ger,
                "gerencia_sigla": ger_sigla,
                "criacao": criacao,
                "area_ha": float(row["area_ha"]),
                "taxa_media": round(float(st["taxa_media"]), 2),
                "cor": get_cor(float(st["taxa_media"])),
                "burned_ha_total": round(float(st["burned_ha_total"]), 1)
            }
        })

    geom_para_2d = json.loads(json.dumps(mapping(gdf_para_simp.iloc[0]["geometry"])))
    geom_para_2d["coordinates"] = strip_z(geom_para_2d["coordinates"])
    para_geo = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": geom_para_2d, "properties": {"name": "Para"}}]
    }
    ucs_geo = {"type": "FeatureCollection", "features": ucs_features}

    # Estruturar series temporais para os graficos por UC
    series_by_uc = {}
    for uid, grp in df_series.groupby("uc_id"):
        grp_sorted = grp.sort_values("ano")
        anos = [int(a) for a in grp_sorted["ano"].tolist()]
        taxas = [round(float(t), 2) for t in grp_sorted["taxa_queimada_pct"].tolist()]
        burned_ha = [round(float(b), 1) for b in grp_sorted["burned_ha"].tolist()]
        
        meta_row = df_meta[df_meta["id"] == uid]
        ano_criacao = int(meta_row["ano_criacao"].values[0]) if not meta_row.empty and not pd.isna(meta_row["ano_criacao"].values[0]) else None
        
        pico_idx = int(grp_sorted["taxa_queimada_pct"].values.argmax())
        pico_ano = anos[pico_idx]
        pico_taxa = taxas[pico_idx]
        
        pre_taxa = round(float(grp_sorted[grp_sorted["ano"] < ano_criacao]["taxa_queimada_pct"].mean()), 2) if ano_criacao else None
        pos_taxa = round(float(grp_sorted[grp_sorted["ano"] >= ano_criacao]["taxa_queimada_pct"].mean()), 2) if ano_criacao else None
        series_by_uc[str(uid)] = {
            "anos": anos,
            "taxas": taxas,
            "burned_ha": burned_ha,
            "ano_criacao": ano_criacao,
            "pico_ano": pico_ano,
            "pico_taxa": pico_taxa,
            "pre_taxa": pre_taxa,
            "pos_taxa": pos_taxa
        }

    # Serie temporal agregada anual geral
    anual_geral = df_series.groupby("ano").agg(
        taxa_media=("taxa_queimada_pct", "mean"),
        burned_ha_sum=("burned_ha", "sum")
    ).reset_index()
    geral_anos = [int(a) for a in anual_geral["ano"].tolist()]
    geral_taxas = [round(float(v), 2) for v in anual_geral["taxa_media"].tolist()]

    clean_ucs_str = json.dumps(ucs_geo, ensure_ascii=False)
    clean_para_str = json.dumps(para_geo, ensure_ascii=False)
    series_json_str = json.dumps(series_by_uc, ensure_ascii=False)
    geral_anos_str = json.dumps(geral_anos)
    geral_taxas_str = json.dumps(geral_taxas)

    html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Dashboard Analítico de Incêndios - IDEFLOR-Bio</title>

  <!-- Leaflet CSS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />

  <!-- Leaflet JS -->
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>

  <!-- Chart.js -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ width: 100%; height: 100%; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0F172A; }}
    #map {{ width: 100%; height: 100%; position: absolute; top: 0; bottom: 0; left: 0; right: 0; }}

    /* Painel Lateral Unificado Inteligente */
    .left-panel {{
      position: absolute;
      top: 14px;
      left: 14px;
      width: 320px;
      background: rgba(255, 255, 255, 0.97);
      backdrop-filter: blur(8px);
      padding: 12px 14px;
      border-radius: 8px;
      box-shadow: 0 4px 22px rgba(0,0,0,0.24);
      border: 1px solid #CBD5E1;
      z-index: 1000;
      transition: transform 0.25s ease;
      max-height: calc(100% - 28px);
      overflow-y: auto;
    }}
    .left-panel.collapsed {{
      transform: translateX(-350px);
    }}
    .panel-toggle-btn {{
      position: absolute;
      top: 14px;
      left: 14px;
      z-index: 999;
      background: #FFFFFF;
      border: 1px solid #CBD5E1;
      border-radius: 6px;
      padding: 6px 10px;
      cursor: pointer;
      font-size: 13px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      display: none;
      font-weight: 600;
      color: #0F172A;
    }}
    .left-panel.collapsed + .panel-toggle-btn {{
      display: block;
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      padding-bottom: 6px;
      border-bottom: 1px solid #E2E8F0;
    }}
    .panel-title {{
      font-size: 13px;
      font-weight: 800;
      color: #0F172A;
      letter-spacing: -0.3px;
    }}
    .panel-collapse-icon {{
      cursor: pointer;
      font-size: 15px;
      color: #64748B;
      border: none;
      background: none;
      padding: 2px 4px;
    }}

    /* Abas de Modo de Analise */
    .mode-tabs {{
      display: flex;
      gap: 4px;
      margin-bottom: 10px;
      background: #F1F5F9;
      padding: 3px;
      border-radius: 6px;
      border: 1px solid #E2E8F0;
    }}
    .mode-tab {{
      flex: 1;
      padding: 6px 4px;
      font-size: 11px;
      font-weight: 700;
      color: #64748B;
      background: transparent;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s ease;
      text-align: center;
    }}
    .mode-tab.active {{
      background: #FFFFFF;
      color: #0F172A;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}

    .filter-group {{
      margin-bottom: 7px;
    }}
    .filter-label {{
      display: block;
      font-size: 10px;
      font-weight: 700;
      color: #334155;
      margin-bottom: 2px;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }}
    .filter-select {{
      width: 100%;
      padding: 5px 8px;
      font-size: 11px;
      border: 1px solid #CBD5E1;
      border-radius: 4px;
      background: #F8FAFC;
      color: #0F172A;
      outline: none;
    }}
    .stats-card {{
      background: #F1F5F9;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 8px 10px;
      margin-top: 8px;
    }}
    .stats-row {{
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      margin-bottom: 3px;
      color: #334155;
    }}
    .stats-row strong {{
      color: #0F172A;
    }}

    /* Container de Grafico Secundario no Painel */
    .mini-chart-box {{
      margin-top: 10px;
      background: #FFFFFF;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 8px;
    }}
    .mini-chart-title {{
      font-size: 10px;
      font-weight: 700;
      color: #334155;
      margin-bottom: 4px;
      display: flex;
      justify-content: space-between;
      text-transform: uppercase;
    }}
    .chart-container-panel {{
      position: relative;
      height: 100px;
      width: 100%;
    }}

    .badge {{
      display: inline-block;
      padding: 2px 6px;
      font-size: 9.5px;
      font-weight: 700;
      border-radius: 3px;
      margin-right: 4px;
      margin-top: 4px;
    }}
    .badge-pi {{ background: #DC2626; color: #FFFFFF; }}
    .badge-us {{ background: #16A34A; color: #FFFFFF; }}
    .badge-ger {{ background: #0284C7; color: #FFFFFF; }}

    .metric-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      margin: 8px 0;
    }}
    .metric-box {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 5px;
      padding: 6px 8px;
      text-align: center;
    }}
    .metric-box .val {{
      font-size: 13px;
      font-weight: 800;
      color: #0F172A;
    }}
    .metric-box .lbl {{
      font-size: 8.5px;
      color: #64748B;
      text-transform: uppercase;
      font-weight: 600;
    }}

    /* Grafico Principal da UC (Chart.js) */
    .chart-box {{
      margin-top: 8px;
      background: #FFFFFF;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 8px;
    }}
    .chart-title {{
      font-size: 10.5px;
      font-weight: 700;
      color: #334155;
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .chart-container-uc {{
      position: relative;
      height: 140px;
      width: 100%;
    }}

    /* Orientacao Superior Centralizada */
    .top-hint {{
      position: absolute;
      top: 14px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(15, 23, 42, 0.88);
      color: #F8FAFC;
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.2px;
      box-shadow: 0 4px 14px rgba(0,0,0,0.25);
      pointer-events: none;
      z-index: 998;
      white-space: nowrap;
    }}


    /* Legenda Cartografica Compacta no Canto Inferior Direito */
    .legend {{
      position: absolute;
      bottom: 14px;
      right: 14px;
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(8px);
      padding: 6px 10px;
      border-radius: 6px;
      box-shadow: 0 4px 18px rgba(0,0,0,0.2);
      border: 1px solid #CBD5E1;
      font-size: 9.5px;
      z-index: 1000;
    }}
    .legend-title {{
      font-weight: 800;
      color: #0F172A;
      margin-bottom: 4px;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      margin-bottom: 2px;
      color: #334155;
      font-size: 9px;
    }}
    .legend-color {{
      width: 13px;
      height: 9px;
      margin-right: 6px;
      border: 1px solid #64748B;
      border-radius: 1px;
    }}

    /* Marco de Criacao Legal */
    .marco-box {{
      background: #FEF2F2;
      border: 1px solid #FECACA;
      border-radius: 6px;
      padding: 6px 8px;
      margin-top: 6px;
    }}
    .marco-title {{
      font-size: 9.5px;
      font-weight: 700;
      color: #991B1B;
      margin-bottom: 3px;
      text-transform: uppercase;
    }}
    .marco-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 4px;
    }}
    .marco-item {{
      text-align: center;
    }}
    .marco-item .val {{
      font-size: 11px;
      font-weight: 700;
      color: #991B1B;
    }}
    .marco-item .lbl {{
      font-size: 8px;
      color: #B91C1C;
    }}

    .leaflet-tooltip-custom {{
      background: rgba(15, 23, 42, 0.92) !important;
      color: #FFFFFF !important;
      border: 1px solid #475569 !important;
      border-radius: 5px !important;
      padding: 5px 8px !important;
      font-size: 11px !important;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    }}
  </style>
</head>
<body>

  <div id="map"></div>

  <!-- Orientacao no topo -->
  <div class="top-hint">Clique em uma UC no mapa ou alterne para Análise por Unidade</div>


  <!-- Painel Lateral Unificado Inteligente -->
  <div id="left-panel" class="left-panel">
    <div class="panel-header">
      <div class="panel-title">PAINEL ANALÍTICO</div>
      <button id="btn-collapse" class="panel-collapse-icon" title="Ocultar painel">«</button>
    </div>

    <!-- Abas / Modos de Analise -->
    <div class="mode-tabs">
      <button id="tab-regional" class="mode-tab active">Visão Regional</button>
      <button id="tab-unidade" class="mode-tab">Análise por Unidade</button>
    </div>

    <!-- SECAO 1: VISAO REGIONAL & GRUPOS -->
    <div id="view-regional">
      <div class="filter-group">
        <label class="filter-label" for="select-gerencia">Gerência Regional:</label>
        <select id="select-gerencia" class="filter-select">
          <option value="TODAS">Todas as 9 Gerências</option>
          <option value="GRB">Belém (GRB)</option>
          <option value="GRCN-I">Calha Norte I (GRCN-I)</option>
          <option value="GRCN-II">Calha Norte II (GRCN-II)</option>
          <option value="GRCN-III">Calha Norte III (GRCN-III)</option>
          <option value="GRM">Marajó (GRM)</option>
          <option value="GRNE">Nordeste Paraense (GRNE)</option>
          <option value="GRA">Araguaia (GRA)</option>
          <option value="GRTUC">Tucuruí (GRTUC)</option>
          <option value="GRX">Xingu (GRX)</option>
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label" for="select-grupo">Grupo SNUC:</label>
        <select id="select-grupo" class="filter-select">
          <option value="TODOS">Todos os Grupos</option>
          <option value="Proteção Integral">Proteção Integral (11 UCs)</option>
          <option value="Uso Sustentável">Uso Sustentável (18 UCs)</option>
        </select>
      </div>

      <div class="stats-card">
        <div class="stats-row"><span>UCs Filtradas:</span><strong id="stat-count">29</strong></div>
        <div class="stats-row"><span>Área Total:</span><strong id="stat-area">21,4 mi ha</strong></div>
        <div class="stats-row"><span>Taxa Média Grupo:</span><strong id="stat-media">1,82% / ano</strong></div>
      </div>

      <!-- Grafico 1 no Painel Lateral: Evolucao Temporal Media do Grupo Filtrado -->
      <div class="mini-chart-box">
        <div class="mini-chart-title">
          <span>Evolução Anual Média (%)</span>
          <span style="font-size: 8.5px; color: #64748B;">{min(geral_anos)} a {max(geral_anos)}</span>
        </div>
        <div class="chart-container-panel">
          <canvas id="group-chart-canvas"></canvas>
        </div>
      </div>
      
      <div style="margin-top: 10px; font-size: 10px; color: #64748B; text-align: center; line-height: 1.35;">
        Clique em qualquer UC no mapa para inspecionar métricas e gráficos individuais
      </div>
    </div>

    <!-- SECAO 2: ANALISE DETALHADA POR UNIDADE -->
    <div id="view-unidade" style="display: none;">
      <div class="filter-group">
        <label class="filter-label" for="select-uc-direct">Unidade de Conservação:</label>
        <select id="select-uc-direct" class="filter-select">
          <option value="">Selecione uma UC na lista...</option>
        </select>
      </div>

      <div id="uc-info-container" style="display: none;">
        <div style="margin-bottom: 6px;">
          <div id="insp-nome" style="font-size: 12px; font-weight: 700; color: #0F172A; line-height: 1.25;">Nome da UC</div>
          <div style="margin-top: 3px; display: flex; gap: 4px; flex-wrap: wrap;">
            <span id="insp-badge-grupo" class="badge">Grupo</span>
            <span id="insp-badge-ger" class="badge badge-ger">Gerência</span>
          </div>
        </div>

        <div class="metric-grid">
          <div class="metric-box">
            <div id="insp-taxa-media" class="val">0,00%</div>
            <div class="lbl">Média Histórica</div>
          </div>
          <div class="metric-box">
            <div id="insp-pico" class="val">0,00%</div>
            <div id="insp-pico-ano" class="lbl">Pico Máximo</div>
          </div>
          <div class="metric-box">
            <div id="insp-area" class="val">0 ha</div>
            <div class="lbl">Área Territorial</div>
          </div>
          <div class="metric-box">
            <div id="insp-total-queimado" class="val">0 ha</div>
            <div class="lbl">Total Queimado Acum.</div>
          </div>
        </div>

        <!-- Marco Legal -->
        <div id="insp-marco-box" class="marco-box">
          <div class="marco-title">Avaliação do Marco Legal</div>
          <div class="marco-grid">
            <div class="marco-item">
              <div id="insp-pre-taxa" class="val">-</div>
              <div class="lbl">Média Pré-Decreto</div>
            </div>
            <div class="marco-item">
              <div id="insp-pos-taxa" class="val">-</div>
              <div class="lbl">Média Pós-Decreto</div>
            </div>
          </div>
        </div>

        <!-- Grafico 2: Serie Historica Completa da UC com Marco Legal -->
        <div class="chart-box">
          <div class="chart-title">
            <span>Série Histórica Anual de Queima (% UC)</span>
            <span id="insp-marco-lbl" style="font-size: 9px; color: #DC2626; font-weight: 700;"></span>
          </div>
          <div class="chart-container-uc">
            <canvas id="uc-chart-canvas"></canvas>
          </div>
          <div style="display: flex; justify-content: center; gap: 12px; margin-top: 4px; font-size: 8.5px; color: #475569;">
            <div style="display: flex; align-items: center; gap: 3px;"><span style="width: 7px; height: 7px; background: #2563EB; border-radius: 1px;"></span>Antes Decreto</div>
            <div style="display: flex; align-items: center; gap: 3px;"><span style="width: 7px; height: 7px; background: #DC2626; border-radius: 1px;"></span>Após Decreto</div>
          </div>
        </div>
      </div>
      
      <div id="uc-empty-state" style="padding: 24px 10px; text-align: center; color: #64748B; font-size: 11px; line-height: 1.4;">
        Selecione uma UC na lista acima ou clique diretamente em qualquer unidade no mapa para carregar seus indicadores e gráficos históricos.
      </div>

      <button id="btn-back-regional" style="margin-top: 10px; width: 100%; padding: 6px; font-size: 11px; font-weight: 700; color: #0284C7; background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 4px; cursor: pointer; transition: all 0.15s ease;">
        « Voltar à Visão Regional
      </button>
    </div>

    <!-- Seletor de Mapa Base (Sempre Acessivel) -->
    <div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid #E2E8F0;">
      <label class="filter-label" for="select-basemap">Mapa Base:</label>
      <select id="select-basemap" class="filter-select">
        <option value="gray">Esri Light Gray Canvas</option>
        <option value="sat">Satélite de Alta Resolução (Esri)</option>
      </select>
    </div>
  </div>

  <button id="btn-expand" class="panel-toggle-btn">Painel Analítico »</button>

  <!-- Legenda Cartografica -->
  <div class="legend">
    <div class="legend-title">Taxa Média de Queima</div>
    <div class="legend-item"><span class="legend-color" style="background: #FFFFB2;"></span>&lt; 0,5% (Baixíssima)</div>
    <div class="legend-item"><span class="legend-color" style="background: #FECC5C;"></span>0,5% a 2% (Baixa)</div>
    <div class="legend-item"><span class="legend-color" style="background: #FD8D3C;"></span>2% a 4% (Moderada)</div>
    <div class="legend-item"><span class="legend-color" style="background: #F03B20;"></span>4% a 7% (Alta)</div>
    <div class="legend-item"><span class="legend-color" style="background: #BD0026;"></span>&gt; 7% (Crítica)</div>
  </div>

  <script>
    const ucsGeo = {clean_ucs_str};
    const paraGeo = {clean_para_str};
    const seriesData = {series_json_str};
    const geralAnos = {geral_anos_str};
    const geralTaxas = {geral_taxas_str};

    // Preencher select direto de UCs ordenado alfabeticamente
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

    // Inicializacao do mapa Leaflet nativo
    const map = L.map('map', {{
      center: [-3.8, -52.5],
      zoom: 6,
      zoomControl: false
    }});

    L.control.zoom({{ position: 'topright' }}).addTo(map);


    // Camadas Base
    const layerGray = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 16,
      attribution: 'Esri &copy; OpenStreetMap'
    }}).addTo(map);

    const layerSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 18,
      attribution: 'Esri &copy; Maxar, Earthstar'
    }});

    // Camada Limite do Para
    L.geoJSON(paraGeo, {{
      style: {{
        color: '#475569',
        fillColor: '#FFFFFF',
        fillOpacity: 0.15,
        weight: 1.8,
        dashArray: '4, 4'
      }}
    }}).addTo(map);

    // Camada das UCs com interatividade
    let selectedLayer = null;
    const layerMap = {{}};

    function styleFeature(feature) {{
      return {{
        fillColor: feature.properties.cor,
        color: '#000000',
        weight: 1.0,
        fillOpacity: 0.88
      }};
    }}

    const ucsLayer = L.geoJSON(ucsGeo, {{
      style: styleFeature,
      onEachFeature: function(feature, layer) {{
        layerMap[feature.properties.id] = layer;
        
        layer.bindTooltip(
          `<strong>${{feature.properties.nome}}</strong><br/><span style="color:#94A3B8;">Gerência: ${{feature.properties.gerencia}} | Média: ${{feature.properties.taxa_media.toFixed(2)}}%</span>`,
          {{ className: 'leaflet-tooltip-custom', sticky: true }}
        );

        layer.on('click', function() {{
          selectUC(feature.properties.id, true);
        }});
      }}
    }}).addTo(map);

    // Ajustar enquadramento inicial
    map.fitBounds([[-9.9, -58.9], [2.5, -46.0]], {{
      paddingTopLeft: [330, 20],
      paddingBottomRight: [20, 20]
    }});

    window.addEventListener('resize', () => map.invalidateSize());
    setTimeout(() => map.invalidateSize(), 300);

    // Controle de recolhimento do painel esquerdo
    const leftPanel = document.getElementById('left-panel');
    const btnCollapse = document.getElementById('btn-collapse');
    const btnExpand = document.getElementById('btn-expand');

    btnCollapse.addEventListener('click', () => {{
      leftPanel.classList.add('collapsed');
      setTimeout(() => map.invalidateSize(), 260);
    }});
    btnExpand.addEventListener('click', () => {{
      leftPanel.classList.remove('collapsed');
      setTimeout(() => map.invalidateSize(), 260);
    }});

    // Instancias globais dos graficos Chart.js
    let groupChart = null;
    let ucChart = null;

    function initGroupChart(labels, data) {{
      const ctx = document.getElementById('group-chart-canvas').getContext('2d');
      if (groupChart) groupChart.destroy();

      groupChart = new Chart(ctx, {{
        type: 'line',
        data: {{
          labels: labels,
          datasets: [{{
            label: 'Taxa Média (%)',
            data: data,
            borderColor: '#0284C7',
            backgroundColor: 'rgba(2, 132, 199, 0.12)',
            fill: true,
            tension: 0.25,
            borderWidth: 1.8,
            pointRadius: 0,
            pointHoverRadius: 4
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                label: (ctx) => `${{ctx.raw.toFixed(2)}}% da área`
              }}
            }}
          }},
          scales: {{
            x: {{
              ticks: {{
                maxTicksLimit: 6,
                font: {{ size: 9 }},
                color: '#64748B'
              }},
              grid: {{ display: false }}
            }},
            y: {{
              ticks: {{
                font: {{ size: 9 }},
                color: '#64748B',
                callback: (v) => v.toFixed(1) + '%'
              }},
              grid: {{ color: '#F1F5F9' }}
            }}
          }}
        }}
      }});
    }}

    // Inicializar grafico do grupo estadual inicial
    initGroupChart(geralAnos, geralTaxas);

    // Alternador de Abas de Analise (Visao Regional vs Analise por Unidade)
    const tabRegional = document.getElementById('tab-regional');
    const tabUnidade = document.getElementById('tab-unidade');
    const viewRegional = document.getElementById('view-regional');
    const viewUnidade = document.getElementById('view-unidade');
    const btnBackRegional = document.getElementById('btn-back-regional');

    let currentMode = 'regional';

    function switchMode(mode) {{
      currentMode = mode;
      if (mode === 'regional') {{
        tabRegional.classList.add('active');
        tabUnidade.classList.remove('active');
        viewRegional.style.display = 'block';
        viewUnidade.style.display = 'none';
        clearSelectionHighlight();
        updateFilters();
      }} else {{
        tabUnidade.classList.add('active');
        tabRegional.classList.remove('active');
        viewUnidade.style.display = 'block';
        viewRegional.style.display = 'none';

        // Na aba de unidade, garante que todas as UCs fiquem visiveis para selecao livre
        ucsLayer.eachLayer(layer => {{
          layer.setStyle({{ opacity: 1, fillOpacity: 0.88 }});
        }});

        if (selDirect.value) {{
          selectUC(parseInt(selDirect.value), false);
        }}
      }}
    }}

    tabRegional.addEventListener('click', () => switchMode('regional'));
    tabUnidade.addEventListener('click', () => switchMode('unidade'));
    btnBackRegional.addEventListener('click', () => switchMode('regional'));

    // Filtros Regionais
    const selGer = document.getElementById('select-gerencia');
    const selGrp = document.getElementById('select-grupo');
    const selBase = document.getElementById('select-basemap');

    function updateFilters() {{
      if (currentMode !== 'regional') return;

      const gerVal = selGer.value;
      const grpVal = selGrp.value;

      let count = 0;
      let totalArea = 0;
      let sumTaxa = 0;
      const activeIds = [];
      const visibleBounds = L.latLngBounds([]);

      ucsLayer.eachLayer(layer => {{
        const p = layer.feature.properties;
        const matchGer = (gerVal === 'TODAS') || (p.gerencia_sigla === gerVal) || (p.gerencia && p.gerencia.includes('(' + gerVal + ')'));
        const matchGrp = (grpVal === 'TODOS') || (p.grupo === grpVal);

        if (matchGer && matchGrp) {{
          layer.setStyle({{ opacity: 1, fillOpacity: 0.88 }});
          visibleBounds.extend(layer.getBounds());
          count++;
          totalArea += (p.area_ha || 0);
          sumTaxa += (p.taxa_media || 0);
          activeIds.push(p.id);
        }} else {{
          layer.setStyle({{ opacity: 0, fillOpacity: 0 }});
        }}
      }});

      // Interacao de zoom dinamica com os filtros regionais
      if (visibleBounds.isValid() && count > 0) {{
        if (gerVal === 'TODAS' && grpVal === 'TODOS') {{
          map.fitBounds([[-9.9, -58.9], [2.5, -46.0]], {{
            paddingTopLeft: [330, 20],
            paddingBottomRight: [20, 20],
            animate: true
          }});
        }} else {{
          map.fitBounds(visibleBounds, {{
            paddingTopLeft: [340, 40],
            paddingBottomRight: [40, 40],
            maxZoom: 10,
            animate: true
          }});
        }}
      }}

      const taxaMedia = count > 0 ? (sumTaxa / count) : 0;
      document.getElementById('stat-count').textContent = count;
      document.getElementById('stat-area').textContent = (totalArea / 1e6).toFixed(1) + ' mi ha';
      document.getElementById('stat-media').textContent = taxaMedia.toFixed(2) + '% / ano';

      // Atualizar grafico do grupo filtrado
      if (activeIds.length > 0) {{
        const annualAverages = geralAnos.map((ano, idx) => {{
          let sum = 0, c = 0;
          activeIds.forEach(id => {{
            const s = seriesData[id];
            if (s && s.taxas && s.taxas[idx] !== undefined) {{
              sum += s.taxas[idx];
              c++;
            }}
          }});
          return c > 0 ? (sum / c) : 0;
        }});
        initGroupChart(geralAnos, annualAverages);
      }}
    }}

    selGer.addEventListener('change', updateFilters);
    selGrp.addEventListener('change', updateFilters);

    selBase.addEventListener('change', (e) => {{
      if (e.target.value === 'sat') {{
        map.removeLayer(layerGray);
        map.addLayer(layerSat);
      }} else {{
        map.removeLayer(layerSat);
        map.addLayer(layerGray);
      }}
    }});

    selDirect.addEventListener('change', (e) => {{
      if (e.target.value) {{
        selectUC(parseInt(e.target.value), false);
      }} else {{
        clearSelectionHighlight();
        document.getElementById('uc-empty-state').style.display = 'block';
        document.getElementById('uc-info-container').style.display = 'none';
      }}
    }});

    function selectUC(id, switchTab) {{
      clearSelectionHighlight();

      const layer = layerMap[id];
      if (!layer) return;

      selectedLayer = layer;
      layer.setStyle({{
        color: '#000000',
        weight: 3.5
      }});
      if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {{
        layer.bringToFront();
      }}

      const feat = layer.feature;
      const p = feat.properties;
      const s = seriesData[id] || {{}};

      selDirect.value = id;

      // Se clicou no mapa enquanto estava na Visao Regional, alterna automaticamente para Analise por Unidade
      if (switchTab && currentMode !== 'unidade') {{
        tabUnidade.classList.add('active');
        tabRegional.classList.remove('active');
        viewUnidade.style.display = 'block';
        viewRegional.style.display = 'none';
        currentMode = 'unidade';
        ucsLayer.eachLayer(l => l.setStyle({{ opacity: 1, fillOpacity: 0.88 }}));
        layer.setStyle({{ color: '#000000', weight: 3.5 }});
      }}

      document.getElementById('uc-empty-state').style.display = 'none';
      document.getElementById('uc-info-container').style.display = 'block';

      document.getElementById('insp-nome').textContent = p.nome;
      const bg = document.getElementById('insp-badge-grupo');
      bg.textContent = p.grupo;
      bg.className = 'badge ' + (p.grupo === 'Proteção Integral' ? 'badge-pi' : 'badge-us');
      document.getElementById('insp-badge-ger').textContent = p.gerencia;

      document.getElementById('insp-taxa-media').textContent = p.taxa_media.toFixed(2) + '%';
      document.getElementById('insp-pico').textContent = (s.pico_taxa || 0).toFixed(2) + '%';
      document.getElementById('insp-pico-ano').textContent = 'Pico Máximo (' + (s.pico_ano || '-') + ')';
      document.getElementById('insp-area').textContent = Math.round(p.area_ha).toLocaleString('pt-BR') + ' ha';
      document.getElementById('insp-total-queimado').textContent = Math.round(p.burned_ha_total || 0).toLocaleString('pt-BR') + ' ha';

      const mlbl = document.getElementById('insp-marco-lbl');
      if (s.ano_criacao) {{
        mlbl.textContent = 'Decreto: ' + s.ano_criacao;
        document.getElementById('insp-pre-taxa').textContent = (s.pre_taxa !== null ? s.pre_taxa.toFixed(2) + '% / ano' : '-');
        document.getElementById('insp-pos-taxa').textContent = (s.pos_taxa !== null ? s.pos_taxa.toFixed(2) + '% / ano' : '-');
        document.getElementById('insp-marco-box').style.display = 'block';
      }} else {{
        mlbl.textContent = '';
        document.getElementById('insp-marco-box').style.display = 'none';
      }}

      renderUCChart(s, s.ano_criacao);

      // Focar na geometria com zoom suave
      map.fitBounds(layer.getBounds(), {{
        paddingTopLeft: [340, 50],
        paddingBottomRight: [50, 50],
        maxZoom: 11,
        animate: true
      }});
    }}

    function clearSelectionHighlight() {{
      if (selectedLayer) {{
        selectedLayer.setStyle({{
          color: '#000000',
          weight: 1.0
        }});
        selectedLayer = null;
      }}
    }}

    function renderUCChart(series, anoCriacao) {{
      const ctx = document.getElementById('uc-chart-canvas').getContext('2d');
      if (ucChart) ucChart.destroy();

      if (!series || !series.anos || series.anos.length === 0) return;

      const anos = series.anos;
      const taxas = series.taxas;

      const bgColors = anos.map(ano => {{
        if (!anoCriacao) return '#2563EB';
        return ano < anoCriacao ? '#2563EB' : '#DC2626';
      }});

      ucChart = new Chart(ctx, {{
        type: 'bar',
        data: {{
          labels: anos,
          datasets: [{{
            label: 'Taxa Queimada (%)',
            data: taxas,
            backgroundColor: bgColors,
            borderRadius: 2
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                title: (items) => `Ano ${{items[0].label}}`,
                label: (ctx) => `${{ctx.raw.toFixed(2)}}% (${{Math.round(series.burned_ha[ctx.dataIndex]).toLocaleString('pt-BR')}} ha)`
              }}
            }}
          }},
          scales: {{
            x: {{
              ticks: {{
                maxTicksLimit: 8,
                font: {{ size: 8.5 }},
                color: '#64748B'
              }},
              grid: {{ display: false }}
            }},
            y: {{
              ticks: {{
                font: {{ size: 8.5 }},
                color: '#64748B',
                callback: (v) => v.toFixed(1) + '%'
              }},
              grid: {{ color: '#F1F5F9' }}
            }}
          }}
        }}
      }});
    }}
  </script>
</body>
</html>
"""

    if save_html:
        out = output_path or (DATA_OUTPUT / "mapa_interativo_fogo_ucs.html")
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"Mapa interativo oficial salvo com sucesso em: {out}")

    return html_template
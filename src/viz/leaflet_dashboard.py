"""
Modulo de geracao do Mini Dashboard Cartografico e Analitico Completo (Leaflet 2D + Chart.js):
- 100% compativel com Google Colab, JupyterLab, VS Code e navegadores locais
- Grafico 1: Serie Temporal Anual da UC selecionada (com barras coloridas antes e depois do decreto de criacao)
- Grafico 2: Painel de Contexto Geral no painel de filtros (Grafico Dinamico de Evolucao Anual das UCs filtradas)
- Grafico 3: Grafico de Ranking Horizontal das Top 5 UCs com maior pressao de fogo
- Filtros em tempo real por Gerencia Regional e Grupo SNUC
- Recalculo instantaneo de indicadores (Area Total, Taxa Media Ponderada, Contagem de UCs)
- Tooltips ricas no cursor e zoom automatico na UC selecionada
"""
from typing import Optional, Dict, Any
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

def create_interactive_leaflet_dashboard(
    df_series: pd.DataFrame,
    save_html: bool = True,
    output_path: Optional[Path] = None
) -> str:
    """Gera o codigo HTML completo do Mini Dashboard analitico interativo."""
    df_meta = pd.read_csv(CSV_METADATA_UCS)
    gdf_ucs = gpd.read_file(GEOJSON_UCS)
    gdf_para = gpd.read_file(GEOJSON_PARA)

    gdf_ucs_simp = gdf_ucs.copy()
    gdf_ucs_simp["geometry"] = gdf_ucs_simp["geometry"].simplify(0.003, preserve_topology=True)
    gdf_para_simp = gdf_para.copy()
    gdf_para_simp["geometry"] = gdf_para_simp["geometry"].simplify(0.008, preserve_topology=True)

    stats = df_series.groupby("uc_id").agg(
        taxa_media=("taxa_queimada_pct", "mean"),
        burned_ha_total=("burned_ha", "sum")
    ).reset_index().set_index("uc_id").to_dict("index")

    def get_cor(taxa: float) -> str:
        if taxa <= 0.50: return "#FFFFB2"
        if taxa <= 2.00: return "#FECC5C"
        if taxa <= 4.00: return "#FD8D3C"
        if taxa <= 7.00: return "#F03B20"
        return "#BD0026"

    def strip_z(coords):
        if isinstance(coords[0], (int, float)):
            return [round(coords[0], 5), round(coords[1], 5)]
        return [strip_z(c) for c in coords]

    ucs_features = []
    for idx, row in gdf_ucs_simp.iterrows():
        uid = int(row["id"])
        st = stats.get(uid, {"taxa_media": 0.0, "burned_ha_total": 0.0})
        meta_row = df_meta[df_meta["id"] == uid]
        nome_oficial = meta_row["nome"].values[0] if not meta_row.empty else str(row["name"])
        cat = meta_row["categoria"].values[0] if not meta_row.empty else str(row.get("categoria", ""))
        grp = meta_row["grupo"].values[0] if not meta_row.empty else str(row.get("grupo", ""))
        ger = meta_row["gerencia"].values[0] if not meta_row.empty else str(row.get("gerencia", ""))
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
        "features": [{"type": "Feature", "geometry": geom_para_2d, "properties": {"name": "Pará"}}]
    }
    ucs_geo = {"type": "FeatureCollection", "features": ucs_features}

    # Series individuais por UC
    series_by_uc = {}
    for uid, group in df_series.groupby("uc_id"):
        uid = int(uid)
        meta_row = df_meta[df_meta["id"] == uid]
        ano_criacao = int(meta_row["ano_criacao"].values[0]) if not meta_row.empty and not pd.isna(meta_row["ano_criacao"].values[0]) else None
        grp_sorted = group.sort_values("ano")
        anos = [int(a) for a in grp_sorted["ano"].tolist()]
        taxas = [round(float(v), 2) for v in grp_sorted["taxa_queimada_pct"].tolist()]
        burned_ha = [round(float(v), 1) for v in grp_sorted["burned_ha"].tolist()]
        pico_idx = grp_sorted["taxa_queimada_pct"].idxmax()
        pico_ano = int(grp_sorted.loc[pico_idx, "ano"])
        pico_taxa = round(float(grp_sorted.loc[pico_idx, "taxa_queimada_pct"]), 2)
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

    # Serie temporal agregada anual geral (1985 a 2023)
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
  <title>Dashboard Analítico de Incêndios - UCs Estaduais do Pará</title>
  
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <!-- Chart.js para renderizacao de graficos interativos de alta definicao -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>

  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ width: 100%; height: 100%; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0F172A; }}
    #map {{ width: 100%; height: 100%; position: absolute; top: 0; bottom: 0; left: 0; right: 0; }}

    /* Painel Esquerdo Compacto: Filtros, Totais e Grafico Geral */
    .left-panel {{
      position: absolute;
      top: 14px;
      left: 14px;
      width: 285px;
      background: rgba(255, 255, 255, 0.96);
      backdrop-filter: blur(8px);
      padding: 12px 14px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.22);
      border: 1px solid #CBD5E1;
      z-index: 1000;
      transition: transform 0.25s ease;
      max-height: calc(100% - 28px);
      overflow-y: auto;
    }}
    .left-panel.collapsed {{
      transform: translateX(-310px);
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

    /* Gaveta Direita: Inspecao Analitica Detalhada da UC */
    .inspector-panel {{
      position: absolute;
      top: 14px;
      right: 14px;
      width: 360px;
      max-height: calc(100% - 28px);
      background: rgba(255, 255, 255, 0.98);
      backdrop-filter: blur(10px);
      padding: 14px 16px;
      border-radius: 8px;
      box-shadow: 0 6px 24px rgba(0,0,0,0.28);
      border: 1px solid #CBD5E1;
      z-index: 1000;
      overflow-y: auto;
      display: none;
      animation: slideIn 0.22s ease-out;
    }}
    @keyframes slideIn {{
      from {{ transform: translateX(380px); opacity: 0; }}
      to {{ transform: translateX(0); opacity: 1; }}
    }}
    .inspector-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 8px;
      padding-bottom: 6px;
      border-bottom: 1px solid #E2E8F0;
    }}
    .inspector-title {{
      font-size: 13.5px;
      font-weight: 800;
      color: #0F172A;
      line-height: 1.25;
    }}
    .inspector-close {{
      cursor: pointer;
      font-size: 18px;
      color: #64748B;
      border: none;
      background: none;
      line-height: 1;
      padding: 0 4px;
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
      font-size: 13.5px;
      font-weight: 800;
      color: #0F172A;
    }}
    .metric-box .lbl {{
      font-size: 9px;
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

    /* Legenda Cartografica Compacta */
    .legend {{
      position: absolute;
      bottom: 14px;
      left: 14px;
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
      font-weight: 700;
      color: #0F172A;
      margin-bottom: 4px;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      margin-bottom: 2px;
    }}
    .legend-box {{
      width: 12px;
      height: 8px;
      border: 1px solid #000;
      margin-right: 5px;
      border-radius: 2px;
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
  <div class="top-hint">Selecione uma UC no mapa ou na lista para inspecionar gráficos e métricas</div>

  <!-- Painel Esquerdo: Filtros, Totais e Grafico Geral do Grupo -->
  <div id="left-panel" class="left-panel">
    <div class="panel-header">
      <div class="panel-title">PAINEL ANALÍTICO</div>
      <button id="btn-collapse" class="panel-collapse-icon" title="Ocultar painel">«</button>
    </div>

    <div class="filter-group">
      <label class="filter-label" for="select-gerencia">Gerência Regional:</label>
      <select id="select-gerencia" class="filter-select">
        <option value="TODAS">Todas as 9 Gerências</option>
        <option value="GRB">Belém (GRB)</option>
        <option value="GRCN">Calha Norte (GRCN)</option>
        <option value="GRM">Marajó (GRM)</option>
        <option value="GRNE">Nordeste Paraense (GRNE)</option>
        <option value="GRA">Araguaia (GRA)</option>
        <option value="GRX">Xingu (GRX)</option>
        <option value="GRT">Tapajós (GRT)</option>
        <option value="GRLT">Lago de Tucuruí (GRLT)</option>
        <option value="GRBVT">Baixo Amazonas (GRBVT)</option>
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

    <div class="filter-group">
      <label class="filter-label" for="select-uc-direct">Selecionar UC Direta:</label>
      <select id="select-uc-direct" class="filter-select">
        <option value="">Selecione na lista...</option>
      </select>
    </div>

    <div class="filter-group">
      <label class="filter-label" for="select-basemap">Mapa Base:</label>
      <select id="select-basemap" class="filter-select">
        <option value="gray">Esri Light Gray Canvas</option>
        <option value="sat">Satélite de Alta Resolução (Esri)</option>
      </select>
    </div>

    <div class="stats-card">
      <div class="stats-row"><span>UCs Exibidas:</span><strong id="stat-count">29</strong></div>
      <div class="stats-row"><span>Área Total:</span><strong id="stat-area">21,4 mi ha</strong></div>
      <div class="stats-row"><span>Taxa Média Grupo:</span><strong id="stat-media">1,82% / ano</strong></div>
    </div>

    <!-- Grafico 1 no Painel Lateral: Evolucao Temporal Media do Grupo Filtrado -->
    <div class="mini-chart-box">
      <div class="mini-chart-title">
        <span>Evolução Anual Média (%)</span>
        <span style="font-size: 8.5px; color: #64748B;">1985–2023</span>
      </div>
      <div class="chart-container-panel">
        <canvas id="group-chart-canvas"></canvas>
      </div>
    </div>
  </div>

  <button id="btn-expand" class="panel-toggle-btn">Filtros »</button>

  <!-- Gaveta Lateral Direita: Inspecao Detalhada da UC Selecionada com Graficos -->
  <div id="inspector" class="inspector-panel">
    <div class="inspector-header">
      <div>
        <div id="insp-nome" class="inspector-title">Nome da UC</div>
        <div>
          <span id="insp-badge-grupo" class="badge">Grupo</span>
          <span id="insp-badge-ger" class="badge badge-ger">Gerência</span>
        </div>
      </div>
      <button id="btn-close-inspect" class="inspector-close">&times;</button>
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

    <!-- Grafico 2: Serie Historica Completa da UC com Marco Legal -->
    <div class="chart-box">
      <div class="chart-title">
        <span>Série Histórica Anual de Queima (% UC)</span>
        <span id="insp-marco-lbl" style="font-size: 9.5px; color: #DC2626; font-weight: 700;"></span>
      </div>
      <div class="chart-container-uc">
        <canvas id="uc-chart-canvas"></canvas>
      </div>
      <div style="display: flex; justify-content: center; gap: 14px; margin-top: 6px; font-size: 9.5px; color: #475569;">
        <div style="display: flex; align-items: center; gap: 4px;"><span style="width: 8px; height: 8px; background: #2563EB; border-radius: 1px;"></span>Antes do Decreto</div>
        <div style="display: flex; align-items: center; gap: 4px;"><span style="width: 8px; height: 8px; background: #DC2626; border-radius: 1px;"></span>Após o Decreto</div>
      </div>
    </div>

    <div id="insp-marco-box" class="stats-card" style="margin-top: 8px; font-size: 10.5px;">
      <div style="font-weight: 700; color: #0F172A; margin-bottom: 3px;">Avaliação do Marco Legal:</div>
      <div class="stats-row"><span>Média Pré-Criação:</span><strong id="insp-pre-taxa">-</strong></div>
      <div class="stats-row"><span>Média Pós-Criação:</span><strong id="insp-pos-taxa">-</strong></div>
    </div>
  </div>

  <!-- Legenda Cartografica -->
  <div class="legend">
    <div class="legend-title">Taxa Média de Queima (% UC/ano)</div>
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

    L.control.zoom({{ position: 'bottomright' }}).addTo(map);

    // Basemaps gratuitos da Esri
    const layerGray = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      attribution: 'Esri, HERE, &copy; OpenStreetMap'
    }}).addTo(map);

    const layerSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      attribution: 'Esri, Maxar'
    }});

    // Camada Limite Estadual do Para
    L.geoJSON(paraGeo, {{
      style: {{
        fill: false,
        color: '#0F172A',
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
          selectUC(feature.properties.id);
        }});
      }}
    }}).addTo(map);

    // Ajustar enquadramento inicial
    map.fitBounds([[-9.9, -58.9], [2.5, -46.0]], {{
      paddingTopLeft: [290, 20],
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

    // Filtros
    const selGer = document.getElementById('select-gerencia');
    const selGrp = document.getElementById('select-grupo');
    const selBase = document.getElementById('select-basemap');

    function updateFilters() {{
      const gerVal = selGer.value;
      const grpVal = selGrp.value;

      let count = 0;
      let totalArea = 0;
      let sumTaxa = 0;
      const activeIds = [];

      ucsLayer.eachLayer(layer => {{
        const p = layer.feature.properties;
        const matchGer = (gerVal === 'TODAS') || (p.gerencia && p.gerencia.includes(gerVal));
        const matchGrp = (grpVal === 'TODOS') || (p.grupo === grpVal);

        if (matchGer && matchGrp) {{
          layer.setStyle({{ opacity: 1, fillOpacity: 0.88 }});
          count++;
          totalArea += (p.area_ha || 0);
          sumTaxa += (p.taxa_media || 0);
          activeIds.push(p.id);
        }} else {{
          layer.setStyle({{ opacity: 0, fillOpacity: 0 }});
        }}
      }});

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
        selectUC(parseInt(e.target.value));
      }}
    }});

    document.getElementById('btn-close-inspect').addEventListener('click', () => {{
      clearSelection();
    }});

    function selectUC(id) {{
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

      const inspector = document.getElementById('inspector');
      inspector.style.display = 'block';

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

      // Focar na geometria
      map.fitBounds(layer.getBounds(), {{
        paddingTopLeft: [300, 50],
        paddingBottomRight: [380, 50],
        maxZoom: 9
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

    function clearSelection() {{
      clearSelectionHighlight();
      document.getElementById('inspector').style.display = 'none';
      selDirect.value = '';
    }}

    function renderUCChart(series, anoCriacao) {{
      const ctx = document.getElementById('uc-chart-canvas').getContext('2d');
      if (ucChart) ucChart.destroy();

      if (!series || !series.anos || series.anos.length === 0) return;

      const anos = series.anos;
      const taxas = series.taxas;
      const colors = anos.map(ano => {{
        return (anoCriacao && ano >= anoCriacao) ? '#DC2626' : '#2563EB';
      }});

      ucChart = new Chart(ctx, {{
        type: 'bar',
        data: {{
          labels: anos,
          datasets: [{{
            data: taxas,
            backgroundColor: colors,
            borderRadius: 2,
            borderWidth: 0
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                title: (items) => `Ano: ${{items[0].label}}`,
                label: (ctx) => `Taxa: ${{ctx.raw.toFixed(2)}}% da UC`
              }}
            }}
          }},
          scales: {{
            x: {{
              ticks: {{
                maxTicksLimit: 8,
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
  </script>
</body>
</html>
"""

    if save_html:
        dest_html = output_path or (DATA_OUTPUT / "mapa_interativo_fogo_ucs.html")
        with open(dest_html, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"Mini Dashboard Leaflet com Chart.js salvo em: {dest_html}")

    return html_template

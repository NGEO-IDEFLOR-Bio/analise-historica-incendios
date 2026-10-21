import sys
from pathlib import Path
sys.path.insert(0, r"H:\Meu Drive\DEV\analise-historica-incendios")

import folium
from folium import plugins
import branca.colormap as cm
import pandas as pd
import geopandas as gpd

from src.config import GEOJSON_UCS, GEOJSON_PARA, DATA_PROCESSED, DATA_OUTPUT

df = pd.read_csv(DATA_PROCESSED / "mapbiomas_fogo_series_1985_2023.csv")
gdf_ucs = gpd.read_file(GEOJSON_UCS)
gdf_para = gpd.read_file(GEOJSON_PARA)

for col in gdf_ucs.columns:
    if pd.api.types.is_datetime64_any_dtype(gdf_ucs[col]):
        gdf_ucs[col] = gdf_ucs[col].astype(str)

gdf_ucs["geometry"] = gdf_ucs.geometry.simplify(0.002, preserve_topology=True)
gdf_para["geometry"] = gdf_para.geometry.simplify(0.005, preserve_topology=True)

stats = df.groupby("uc_nome").agg(
    taxa_media=("taxa_queimada_pct", "mean"),
    burned_total=("burned_ha", "sum")
).reset_index().set_index("uc_nome").to_dict("index")

gdf_ucs["taxa_media"] = gdf_ucs["name"].map(lambda x: round(stats.get(x, {}).get("taxa_media", 0.0), 2))
gdf_ucs["burned_total"] = gdf_ucs["name"].map(lambda x: round(stats.get(x, {}).get("burned_total", 0.0), 1))

m = folium.Map(location=[-3.8, -52.5], zoom_start=6, tiles=None)

# 1. Esri Light Gray Canvas (gratuito e clean)
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

# 3. OpenStreetMap
folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="&copy; OpenStreetMap contributors",
    name="OpenStreetMap (Vias e Localidades)",
    control=True
).add_to(m)

# Limite Estadual do Pará
folium.GeoJson(
    gdf_para,
    name="Limite Estadual do Pará",
    style_function=lambda x: {"fillColor": "transparent", "color": "#0F172A", "weight": 2, "dashArray": "4, 4"}
).add_to(m)

def get_cor(t):
    if t <= 0.5: return "#FFFFB2"
    if t <= 2.0: return "#FECC5C"
    if t <= 4.0: return "#FD8D3C"
    if t <= 7.0: return "#F03B20"
    return "#BD0026"

# Separação por Gerências Regionais como camadas ativáveis/desativáveis
gerencias = sorted([g for g in gdf_ucs["gerencia"].dropna().unique()])
for ger in gerencias:
    subset = gdf_ucs[gdf_ucs["gerencia"] == ger]
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

# Escala de cores temática
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

out_html = DATA_OUTPUT / "mapa_interativo_fogo_ucs.html"
m.save(str(out_html))
print(f"Mapa interativo oficial salvo com sucesso em: {out_html}")

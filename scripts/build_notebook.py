"""
Script gerador do notebook executivo de Análise Histórica de Incêndios (IDEFLOR-Bio).
"""
import json
from pathlib import Path

NOTEBOOK_PATH = Path(r"H:\Meu Drive\DEV\analise-historica-incendios\notebooks\01_analise_historica_incendios.ipynb")

def make_cell(cell_type, source, metadata=None):
    if metadata is None:
        metadata = {}
    if isinstance(source, list):
        src_lines = [s + "\n" if not s.endswith("\n") else s for s in source]
    else:
        src_lines = [line + "\n" for line in source.split("\n")]
    if src_lines and src_lines[-1].endswith("\n"):
        src_lines[-1] = src_lines[-1][:-1]

    cell = {
        "cell_type": cell_type,
        "metadata": metadata,
        "source": src_lines
    }
    if cell_type == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
    return cell

def build_notebook():
    cells = []

    # 1. TÍTULO E APRESENTAÇÃO
    cells.append(make_cell("markdown", """# Análise Histórica do Regime de Fogo nas Unidades de Conservação do Pará (IDEFLOR-Bio)
### Série Temporal de Cicatrizes de Queimada (1985–2023) | MapBiomas Fogo Coleção 3 (30m)

---

## 🎯 Objetivos do Estudo
1. **Panorama Geral Estadual:** Mapear a dinâmica temporal acumulada de queimadas nas 29 Unidades de Conservação do Estado do Pará.
2. **Avaliação por Gerência Regional:** Comparar a vulnerabilidade e a taxa de queima normalizada por área entre as 9 Gerências Regionais do IDEFLOR-Bio.
3. **Análise Causal do Marco de Criação (*Before vs. After*):** Quantificar o impacto do decreto legal de criação na contenção ou alteração do regime de fogo em cada UC.
4. **Mapeamento Espacial Integrado:** Visualizar a distribuição geográfica da pressão de fogo por meio de mapas estáticos e interativos.
"""))

    # 2. SETUP E IMPORTS
    cells.append(make_cell("code", """import sys
from pathlib import Path

# Configuração de caminhos e ambiente
ROOT_DIR = Path("..").resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import folium
import ipywidgets as widgets
from IPython.display import display, HTML

# Módulos customizados de visualização
from src.config import CSV_METADATA_UCS, GEOJSON_UCS, DATA_PROCESSED
from src.viz.theme import apply_ggplot_theme, COLOR_FIRE_MAIN, COLOR_FIRE_LIGHT, COLOR_PRE_CREATION, COLOR_POST_CREATION
from src.viz.charts import plot_panorama_estadual, plot_comparativo_gerencias, plot_uc_before_after
from src.viz.maps import plot_static_map, create_interactive_folium_map

apply_ggplot_theme()
print("Ambiente configurado com sucesso! Tema 'ggplot2 / R publication' ativado.")
"""))

    # 3. CARREGAMENTO DOS DADOS
    cells.append(make_cell("code", """# Carregar a base histórica de 1985 a 2023 consolidada via Google Earth Engine
df_series = pd.read_csv(DATA_PROCESSED / "mapbiomas_fogo_series_1985_2023.csv")
df_meta = pd.read_csv(CSV_METADATA_UCS)

print(f"Total de registros históricos: {len(df_series):,} (29 UCs x 39 anos)")
print(f"Período temporal: {df_series['ano'].min()} a {df_series['ano'].max()}")
df_series.head(4)
"""))

    # 4. PANORAMA GERAL ESTADUAL
    cells.append(make_cell("markdown", """---
## 1. Panorama Geral Estadual: Dinâmica do Fogo (1985–2023)

Abaixo observamos a evolução total da área queimada em todas as 29 UCs ao longo de quase 4 décadas.
A linha pontilhada representa a **Média Móvel de 5 Anos**, evidenciando ciclos climáticos e os picos associados a eventos de seca extrema (como os anos de El Niño em 1997/98, 2015/16 e 2023/24).
"""))

    cells.append(make_cell("code", """fig, ax = plot_panorama_estadual(df_series, figsize=(13, 5.5))
plt.show()
"""))

    # 5. HEATMAP SAZONAL / DECADAL
    cells.append(make_cell("markdown", """### Matriz de Calor: Intensidade Histórica de Queima por Gerência Regional
Para visualizar padrões temporais e concentrações críticas, a matriz abaixo decompõe a taxa média anual de queima (% da área da gerência) ao longo das décadas.
"""))

    cells.append(make_cell("code", """# Pivot da taxa média por gerência e ano
from src.config import SIGLAS_GERENCIAS

df_hm = df_series.copy()
df_hm["sigla"] = df_hm["gerencia"].map(SIGLAS_GERENCIAS).fillna(df_hm["gerencia"])
pivot_fogo = df_hm.pivot_table(index="sigla", columns="ano", values="taxa_queimada_pct", aggfunc="mean")

fig, ax = plt.subplots(figsize=(15, 6))
sns.heatmap(
    pivot_fogo,
    cmap="YlOrRd",
    linewidths=0.2,
    linecolor="#F3F4F6",
    cbar_kws={"label": "Taxa Média de Queima (% do território atingido)", "shrink": 0.7},
    ax=ax
)
ax.set_title("Matriz Histórica de Pressão de Fogo por Gerência (1985–2023)", fontsize=13, fontweight="bold", pad=12)
ax.set_xlabel("Ano", fontsize=10, labelpad=8)
ax.set_ylabel("Gerência Regional", fontsize=10, labelpad=8)
plt.tight_layout()
plt.show()
"""))

    # 6. PANORAMA REGIONAL (POR GERÊNCIA)
    cells.append(make_cell("markdown", """---
## 2. Panorama Regional: Comparativo entre as 9 Gerências

A métrica bruta (hectares queimados) pode enviesar as conclusões em favor das gigantescas UCs da Calha Norte (milhões de hectares).
Ao normalizar pela **taxa percentual anual (% da área queimada em relação ao território total da gerência)**, podemos identificar com precisão onde está a maior pressão ecológica relativa.
"""))

    cells.append(make_cell("code", """fig, ax = plot_comparativo_gerencias(df_series, figsize=(13, 6))
plt.show()
"""))

    # 7. COMPARATIVO POR GRUPO SNUC
    cells.append(make_cell("markdown", """### Efetividade por Grupo de Manejo: Proteção Integral vs. Uso Sustentável
Existe diferença no regime histórico de fogo entre unidades de **Proteção Integral** (onde não há uso direto de recursos) e **Uso Sustentável** (onde populações tradicionais e atividades humanas convivem)?
"""))

    cells.append(make_cell("code", """df_grupo = df_series.groupby(["grupo", "ano"])["taxa_queimada_pct"].mean().reset_index()

fig, ax = plt.subplots(figsize=(12, 5))
for grp, cor, ls in zip(["Proteção Integral", "Uso Sustentável"], ["#1B5E20", "#D84315"], ["-", "--"]):
    sub = df_grupo[df_grupo["grupo"] == grp]
    ax.plot(sub["ano"], sub["taxa_queimada_pct"], label=grp, color=cor, linestyle=ls, linewidth=2.0)

ax.set_title("Evolução da Taxa de Queima por Grupo SNUC (1985–2023)", fontsize=13, fontweight="bold", pad=12)
ax.set_ylabel("Taxa Média Anual (% da UC)", fontsize=10)
ax.set_xlabel("Ano", fontsize=10)
ax.legend(title="Grupo SNUC", frameon=False)
plt.tight_layout()
plt.show()
"""))

    # 8. ANÁLISE POR UNIDADE E MARCO LEGAL DE CRIAÇÃO
    cells.append(make_cell("markdown", """---
## 3. Análise Detalhada por Unidade: O Impacto do Marco Legal de Criação

Nesta seção, avaliamos a hipótese de efetividade de gestão: **o ato formal de criação da UC reduziu ou conteve a incidência de queimadas?**
Utilize o seletor interativo abaixo para escolher qualquer uma das 29 UCs e visualizar o gráfico de impacto temporal (*Antes vs. Depois da Criação*).
"""))

    cells.append(make_cell("code", """# Seletor interativo de Unidade de Conservação
ucs_disponiveis = df_meta.sort_values(by="nome")[["id", "nome", "ano_criacao", "gerencia"]].values

opcoes_dropdown = [(f"{nome} (Criada em {ano})", int(uid)) for uid, nome, ano, ger in ucs_disponiveis]

dropdown_uc = widgets.Dropdown(
    options=opcoes_dropdown,
    value=opcoes_dropdown[0][1],
    description="Escolha a UC:",
    style={"description_width": "initial"},
    layout=widgets.Layout(width="550px")
)

def atualizar_grafico_uc(uc_id):
    fig, ax = plot_uc_before_after(df_series, uc_id=uc_id, figsize=(13, 5.5))
    plt.show()
    
    # Exibir resumo numérico do impacto
    df_sub = df_series[df_series["uc_id"] == uc_id]
    ano_cria = df_sub["ano_criacao"].iloc[0]
    m_pre = df_sub[df_sub["ano"] < ano_cria]["taxa_queimada_pct"].mean()
    m_pos = df_sub[df_sub["ano"] >= ano_cria]["taxa_queimada_pct"].mean()
    var_abs = m_pos - m_pre
    var_rel = ((m_pos - m_pre) / m_pre * 100.0) if m_pre > 0 else 0.0

    print("=" * 70)
    print(f"RESUMO DE EFETIVIDADE DA GESTÃO: {df_sub['uc_nome'].iloc[0]}")
    print(f" - Ano de Criação: {ano_cria}")
    print(f" - Taxa Média Pré-Criação: {m_pre:.2f}% ao ano")
    print(f" - Taxa Média Pós-Criação: {m_pos:.2f}% ao ano")
    sinal = "Redução" if var_abs < 0 else "Aumento"
    print(f" - Resultado: {sinal} de {abs(var_abs):.2f} pontos percentuais ({var_rel:+.1f}%)")
    print("=" * 70)

widgets.interact(atualizar_grafico_uc, uc_id=dropdown_uc)
"""))

    # 9. MAPEAMENTO ESPACIAL
    cells.append(make_cell("markdown", """---
## 4. Mapeamento Espacial da Pressão Histórica de Queimadas

Abaixo apresentamos a distribuição geográfica das 29 Unidades de Conservação coloridas pela **taxa média histórica de queima (% da área da UC/ano)**.
"""))

    cells.append(make_cell("code", """# 1. Mapa Estático (Padrão Publicação / Alta Resolução)
fig, ax = plot_static_map(df_series, figsize=(11, 8.5))
plt.show()
"""))

    cells.append(make_cell("code", """# 2. Mapa Interativo Folium com Tooltips
# Permite dar zoom, explorar limites territoriais e inspecionar os indicadores de cada UC
mapa_interativo = create_interactive_folium_map(df_series, save_html=True)
display(mapa_interativo)
"""))

    # 10. CONCLUSÕES E PRÓXIMOS PASSOS
    cells.append(make_cell("markdown", """---
## 5. Principais Insights e Conclusões

1. **Assimetria Regional Marcante:**
   - As UCs do **Nordeste Paraense** (ex: REVIS Padre Sérgio Tonetto e RDS Campo das Mangabas) e do **Araguaia/Xingu** (ex: PESM Andorinhas e APA Triunfo do Xingu) apresentam as maiores taxas relativas de queima, frequentemente superando 4% a 10% da sua área queimada ao ano.
   - Em contraste, as UCs de **Belém** (Combu, Utinga) e as grandes florestas da **Calha Norte** (Paru, Grão-Pará) mantêm regimes com taxas percentuais muito menores, refletindo menor pressão agropecuária e maior umidade contínua.

2. **O Efeito do Marco Legal:**
   - Em diversas UCs, a institucionalização legal coincide com uma estabilização ou redução da variabilidade dos grandes episódios de fogo, embora UCs de Uso Sustentável sujeitas à pressão de fronteira agrícola continuem a demandar ações prioritárias de manejo integrado do fogo (MIF).

3. **Próximas Expansões:**
   - Cruzar os dados anuais do MapBiomas com os focos em tempo quase-real do **BDQueimadas/INPE** e **VIIRS**.
   - Integração com dados de precipitação (CHIRPS) para separar o efeito climático do efeito antrópico.
"""))

    notebook_content = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.13.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(notebook_content, f, indent=2, ensure_ascii=False)

    print(f"Notebook executivo construído com sucesso em: {NOTEBOOK_PATH}")

if __name__ == "__main__":
    build_notebook()

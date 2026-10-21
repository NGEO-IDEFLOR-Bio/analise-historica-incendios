"""
Script gerador do notebook executivo de Analise Historica de Incendios (IDEFLOR-Bio).
Padronizado em estilo documental, sem emojis e sem travessoes.
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

    # 1. TITULO, BADGE DO COLAB E CONTEXTUALIZACAO
    cells.append(make_cell("markdown", """# Analise Historica do Regime de Fogo nas Unidades de Conservacao do Para (IDEFLOR-Bio)
### Serie Temporal de Cicatrizes de Queimada (1985 a 2023) | MapBiomas Fogo Colecao 3 (30 metros)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/NGEO-IDEFLOR-Bio/analise-historica-incendios/blob/main/notebooks/01_analise_historica_incendios.ipynb)

Este caderno documenta a analise espaco-temporal de cicatrizes de fogo registradas entre 1985 e 2023 nas 29 Unidades de Conservacao Estaduais do Para sob gestao do IDEFLOR-Bio. Os objetivos compreendem o levantamento da dinamica estadual, a comparacao normalizada por area entre Gerencias Regionais, a segregacao por grupo do SNUC (Protecao Integral versus Uso Sustentavel) e a verificacao empirica do efeito do decreto de criacao de cada unidade sobre a taxa de queima territorial.
"""))

    # 2. INSTALACAO DE DEPENDENCIAS (GOOGLE COLAB)
    cells.append(make_cell("code", """# Instalacao de dependencias (necessario na execucao via Google Colab)
!pip install -q geopandas matplotlib seaborn ipywidgets
"""))

    # 3. SUPORTE A EXECUCAO E SINCRONIZACAO NO GOOGLE COLAB
    cells.append(make_cell("code", """# Sincronizacao do repositorio e configuracao de diretorios no Google Colab
import sys
import os
from pathlib import Path

IN_COLAB = "google.colab" in sys.modules

if IN_COLAB:
    print("Ambiente Google Colab detectado. Sincronizando repositorio oficial...")
    # Fixa o diretorio base em /content para evitar aninhamento de pastas
    os.chdir("/content")
    repo_dir = Path("/content/analise-historica-incendios")

    if not repo_dir.exists():
        !git clone https://github.com/NGEO-IDEFLOR-Bio/analise-historica-incendios.git
        os.chdir(repo_dir)
    else:
        os.chdir(repo_dir)
        !git reset --hard origin/main
        !git pull origin main

    ROOT_DIR = repo_dir

    # Remove eventuais caminhos duplicados de sessoes anteriores do sys.path
    sys.path = [p for p in sys.path if "analise-historica-incendios" not in p]
    sys.path.insert(0, str(ROOT_DIR))

    # Limpa modulos pre-carregados de src para forcar recarregamento dos arquivos atualizados
    for mod in list(sys.modules.keys()):
        if mod.startswith("src"):
            del sys.modules[mod]
else:
    ROOT_DIR = Path("..").resolve()
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))

print(f"Raiz do projeto configurada: {ROOT_DIR}")
"""))

    # 4. SETUP E IMPORTACOES
    cells.append(make_cell("code", """import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import ipywidgets as widgets
from IPython.display import display

from src.config import CSV_METADATA_UCS, GEOJSON_UCS, DATA_PROCESSED
from src.viz.theme import apply_ggplot_theme, COLOR_FIRE_MAIN, COLOR_FIRE_LIGHT, COLOR_PRE_CREATION, COLOR_POST_CREATION
from src.viz.charts import plot_panorama_estadual, plot_comparativo_gerencias, plot_uc_before_after
from src.viz.maps import plot_static_map, create_interactive_folium_map, display_maplibre_in_notebook

apply_ggplot_theme()
print("Modulos carregados e padronizacao grafica ativada.")
"""))

    # 4. CARREGAMENTO DOS DADOS
    cells.append(make_cell("code", """# Carregamento da serie historica anual processada via Google Earth Engine
df_series = pd.read_csv(DATA_PROCESSED / "mapbiomas_fogo_series_1985_2023.csv")
df_meta = pd.read_csv(CSV_METADATA_UCS)

print(f"Registros anuais carregados: {len(df_series)} (29 UCs x 39 anos)")
print(f"Intervalo temporal: {df_series['ano'].min()} a {df_series['ano'].max()}")
df_series.head(5)
"""))

    # 5. PANORAMA GERAL ESTADUAL
    cells.append(make_cell("markdown", """## 1. Panorama Geral Estadual: Dinamica Anual de Queimadas (1985 a 2023)

O grafico abaixo apresenta a soma anual da area queimada no conjunto das 29 Unidades de Conservacao. A linha tracejada corresponde a media movel centrada de 5 anos para atenuacao da variabilidade interanual. As anotacoes apontam os anos com maior extensao territorial queimada, associados a fenomenos climaticos de seca severa como os eventos de El Nino.
"""))

    cells.append(make_cell("code", """fig, ax = plot_panorama_estadual(df_series, figsize=(13, 5.5))
plt.show()
"""))

    # 6. MATRIZ DE CALOR POR GERENCIA
    cells.append(make_cell("markdown", """### Matriz de Intensidade Temporal por Gerencia Regional

A distribuicao matricial abaixo indica a taxa media anual de queima (percentual da area da gerencia atingida) por ano e por regional administrativa do IDEFLOR-Bio.
"""))

    cells.append(make_cell("code", """from src.config import SIGLAS_GERENCIAS

df_hm = df_series.copy()
df_hm["sigla"] = df_hm["gerencia"].map(SIGLAS_GERENCIAS).fillna(df_hm["gerencia"])
pivot_fogo = df_hm.pivot_table(index="sigla", columns="ano", values="taxa_queimada_pct", aggfunc="mean")

fig, ax = plt.subplots(figsize=(15, 6))
sns.heatmap(
    pivot_fogo,
    cmap="YlOrRd",
    linewidths=0.2,
    linecolor="#F3F4F6",
    cbar_kws={"label": "Taxa Media de Queima (% do territorio atingido)", "shrink": 0.7},
    ax=ax
)
ax.set_title("Matriz Historica de Pressao de Fogo por Gerencia Regional (1985 a 2023)", fontsize=13, fontweight="bold", pad=12)
ax.set_xlabel("Ano", fontsize=10, labelpad=8)
ax.set_ylabel("Gerencia Regional", fontsize=10, labelpad=8)
plt.tight_layout()
plt.show()
"""))

    # 7. COMPARATIVO REGIONAL NORMALIZADO
    cells.append(make_cell("markdown", """## 2. Comparativo Regional: Normalizacao por Area Territorial

A comparacao direta em hectares absolutos produz distorcao analitica devido a diferenca de escala entre as regionais (a exemplo da Calha Norte, com milhoes de hectares, em relacao a Belem ou Nordeste). O indicador utilizado a seguir corresponde a taxa media anual percentual de queima, calculada sobre a area total de cada gerencia.
"""))

    cells.append(make_cell("code", """fig, ax = plot_comparativo_gerencias(df_series, figsize=(13, 6))
plt.show()
"""))

    # 8. COMPARATIVO POR GRUPO SNUC
    cells.append(make_cell("markdown", """### Comportamento Temporal por Categoria de Manejo (SNUC)

Comparacao das medias anuais entre unidades de Protecao Integral e unidades de Uso Sustentavel.
"""))

    cells.append(make_cell("code", """df_grupo = df_series.groupby(["grupo", "ano"])["taxa_queimada_pct"].mean().reset_index()

fig, ax = plt.subplots(figsize=(12, 5))
for grp, cor, ls in zip(["Proteção Integral", "Uso Sustentável"], ["#1B5E20", "#D84315"], ["-", "--"]):
    sub = df_grupo[df_grupo["grupo"] == grp]
    ax.plot(sub["ano"], sub["taxa_queimada_pct"], label=grp, color=cor, linestyle=ls, linewidth=2.0)

ax.set_title("Evolucao da Taxa Media de Queima por Grupo SNUC (1985 a 2023)", fontsize=13, fontweight="bold", pad=12)
ax.set_ylabel("Taxa Media Anual (% da UC)", fontsize=10)
ax.set_xlabel("Ano", fontsize=10)
ax.legend(title="Grupo SNUC", frameon=False)
plt.tight_layout()
plt.show()
"""))

    # 9. ANALISE POR UNIDADE E MARCO LEGAL
    cells.append(make_cell("markdown", """## 3. Analise por Unidade de Conservacao: Impacto do Marco Legal de Criacao

A secao a seguir viabiliza a verificacao da taxa anual de queima antes e apos a data formal de criacao de cada unidade. O seletor interativo permite inspecionar individualmente qualquer uma das 29 areas protegidas.
"""))

    cells.append(make_cell("code", """# Menu seletor de Unidades de Conservacao
ucs_disponiveis = df_meta.sort_values(by="nome")[["id", "nome", "ano_criacao", "gerencia"]].values
opcoes_dropdown = [(f"{nome} (Criacao: {ano})", int(uid)) for uid, nome, ano, ger in ucs_disponiveis]

dropdown_uc = widgets.Dropdown(
    options=opcoes_dropdown,
    value=opcoes_dropdown[0][1],
    description="UC Selecionada:",
    style={"description_width": "initial"},
    layout=widgets.Layout(width="550px")
)

def atualizar_grafico_uc(uc_id):
    fig, ax = plot_uc_before_after(df_series, uc_id=uc_id, figsize=(13, 5.5))
    plt.show()
    
    df_sub = df_series[df_series["uc_id"] == uc_id]
    ano_cria = df_sub["ano_criacao"].iloc[0]
    m_pre = df_sub[df_sub["ano"] < ano_cria]["taxa_queimada_pct"].mean()
    m_pos = df_sub[df_sub["ano"] >= ano_cria]["taxa_queimada_pct"].mean()
    var_abs = m_pos - m_pre
    var_rel = ((m_pos - m_pre) / m_pre * 100.0) if m_pre > 0 else 0.0

    print("=" * 70)
    print(f"RELATORIO ANALITICO: {df_sub['uc_nome'].iloc[0]}")
    print(f"Ano do Decreto Legal de Criacao: {ano_cria}")
    print(f"Taxa Media Pre Criacao: {m_pre:.2f}% ao ano")
    print(f"Taxa Media Pos Criacao: {m_pos:.2f}% ao ano")
    rotulo = "Reducao" if var_abs < 0 else "Aumento"
    print(f"Resultado Comparativo: {rotulo} de {abs(var_abs):.2f} pontos percentuais ({var_rel:+.1f}%)")
    print("=" * 70)

widgets.interact(atualizar_grafico_uc, uc_id=dropdown_uc)
"""))

    # 10. MAPEAMENTO CARTOGRAFICO
    cells.append(make_cell("markdown", """## 4. Mapeamento Cartografico da Pressao Historica de Queimadas

Espacializacao geografica das 29 Unidades de Conservacao classificadas pela taxa media anual de queima registrada entre 1985 e 2023.
"""))

    cells.append(make_cell("code", """# Prancha cartografica oficial com contexto regional, escala grafica e mapa de enquadramento
fig, ax = plot_static_map(df_series, figsize=(16, 11))
plt.show()
"""))

    cells.append(make_cell("markdown", """### Mapa Interativo de Navegação Espacial (Leaflet / Folium)

Mapa vetorial interativo com navegação fluida, sem restrição ou cobrança de chaves de API. Oferece controle por camadas temáticas individuais para cada Gerência Regional, alternância entre três bases cartográficas (Esri Canvas Claro, Satélite de Alta Resolução Esri Imagery e OpenStreetMap), escala cromática de queima histórica e tooltips cadastrais completas ao passar o cursor sobre as Unidades de Conservação.
"""))

    cells.append(make_cell("code", """# Geração e exibição do mapa interativo Folium diretamente na célula
mapa_interativo = create_interactive_folium_map(df_series, save_html=True)
display(mapa_interativo)
"""))

    # 11. SINTESE CONCLUSIVA
    cells.append(make_cell("markdown", """## 5. Sintese dos Resultados

1. Heterogeneidade Regional:
As maiores taxas relativas de queima concentram-se no Nordeste Paraense (REVIS Padre Sergio Tonetto, RDS Campo das Mangabas) e no eixo Araguaia e Xingu (Parque Estadual Serra dos Martirios/Andorinhas, APA Triunfo do Xingu). Nestas unidades, as taxas medias anuais situam-se entre 3.9% e 10.4% da superficie territorial total. Em contrapartida, as unidades da Regiao Metropolitana de Belem e os blocos contiguos da Calha Norte mantem medias anuais inferiores a 0.5%.

2. Avaliacao do Marco Legal:
O efeito temporal do decreto legal evidencia estabilizacao da variabilidade extrema de queima em unidades de Protecao Integral, ao passo que areas de Uso Sustentavel inseridas em zonas de consolidacao agropecuaria continuam sob pressao frequente de fogo, indicando necessidade de intensificacao do Manejo Integrado do Fogo (MIF).
"""))

    notebook_content = {
        "cells": cells,
        "metadata": {
            "colab": {
                "name": "01_analise_historica_incendios.ipynb",
                "provenance": []
            },
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

    print(f"Notebook atualizado com sucesso em: {NOTEBOOK_PATH}")

if __name__ == "__main__":
    build_notebook()

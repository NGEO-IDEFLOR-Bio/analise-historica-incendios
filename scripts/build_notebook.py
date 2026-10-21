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
### Serie Temporal Integrada de Cicatrizes de Queimada (1985 a 2026) | MapBiomas Fogo & MODIS GEE

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/NGEO-IDEFLOR-Bio/analise-historica-incendios/blob/main/notebooks/01_analise_historica_incendios.ipynb)

Este caderno documenta a analise espaco-temporal de cicatrizes de fogo registradas entre 1985 e 2026 nas 29 Unidades de Conservacao Estaduais do Para sob gestao do IDEFLOR-Bio. Os dados integram a serie historica de 30 metros do MapBiomas Fogo (1985 a 2023) com o monitoramento de cicatrizes mensais MODIS MCD64A1 via Google Earth Engine (2024 a 2026). Os objetivos compreendem o levantamento da dinamica estadual, a comparacao normalizada por area entre Gerencias Regionais, a segregacao por grupo do SNUC (Protecao Integral versus Uso Sustentavel) e a verificacao empirica do efeito do decreto de criacao de cada unidade sobre a taxa de queima territorial.
"""))

    # 2. INSTALACAO DE DEPENDENCIAS (GOOGLE COLAB)
    cells.append(make_cell("code", """# Instalacao de dependencias (necessario na execucao via Google Colab)
!pip install -q geopandas matplotlib seaborn ipywidgets earthengine-api
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

    # 4. CONEXAO COM O GOOGLE EARTH ENGINE (INTERATIVA NO COLAB)
    cells.append(make_cell("markdown", """### Conexao Universal com o Google Earth Engine (GEE)

Este notebook conta com autenticacao adaptativa:
* **No Google Colab:** Conecta de forma interativa com a sua conta Google em um pop-up de 1 clique, sem necessidade de arquivos de chave privada. O Google Earth Engine requer a indicacao de um Google Cloud Project associado a sua conta.
* **No ambiente local:** Utiliza credenciais de Service Account ou sessao de usuario ativa configurada via `gcloud`.

> Caso voce queira conectar ao Earth Engine no Colab para reprocessamento ou extracao sob demanda, insira o ID do seu projeto Google Cloud na variavel `GEE_PROJECT` abaixo (ex: `"ee-seu-usuario"` ou `"meu-projeto"`).
> Se nao tiver ou preferir nao conectar ao GEE agora, a base historica integrada (1985 a 2026) ja vem pre-processada e pronta no repositorio para execucao imediata de todas as analises, matrizes e mapas!
"""))

    cells.append(make_cell("code", """# Configuracao do Projeto Google Cloud e Inicializacao do Earth Engine
# Defina o ID do seu Google Cloud Project com acesso ao Earth Engine:
GEE_PROJECT = ""  # Exemplo: "ee-seu-usuario" ou "meu-projeto-gee"

from src.gee_auth import init_gee

try:
    init_gee(project_id=GEE_PROJECT if GEE_PROJECT else None)
    print("Google Earth Engine inicializado com sucesso!")
except Exception as e:
    print(f"Aviso: GEE nao inicializado ({e}). As analises continuam normalmente usando os dados locais pre-processados.")
"""))

    # 5. SETUP E IMPORTACOES
    cells.append(make_cell("code", """import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import ipywidgets as widgets
from IPython.display import display, clear_output

from src.config import CSV_METADATA_UCS, GEOJSON_UCS, DATA_PROCESSED
from src.viz.theme import apply_ggplot_theme, COLOR_FIRE_MAIN, COLOR_FIRE_LIGHT, COLOR_PRE_CREATION, COLOR_POST_CREATION
from src.viz.charts import (
    plot_panorama_estadual,
    plot_comparativo_gerencias,
    plot_uc_before_after,
    plot_matriz_intensidade_unidades
)
from src.viz.maps import plot_static_map, create_interactive_maplibre_map, display_maplibre_in_notebook

apply_ggplot_theme()
print("Modulos carregados e padronizacao grafica ativada.")
"""))

    # 6. CARREGAMENTO DOS DADOS
    cells.append(make_cell("code", """# Carregamento da serie historica anual integrada (1985 a 2026)
csv_full = DATA_PROCESSED / "mapbiomas_fogo_series_1985_2026.csv"
if not csv_full.exists():
    csv_full = DATA_PROCESSED / "mapbiomas_fogo_series_1985_2023.csv"

df_series = pd.read_csv(csv_full)
df_meta = pd.read_csv(CSV_METADATA_UCS)

print(f"Registros anuais carregados: {len(df_series)} (29 UCs)")
print(f"Intervalo temporal analisado: {df_series['ano'].min()} a {df_series['ano'].max()} ({df_series['ano'].nunique()} anos)")
df_series.head(5)
"""))

    # 7. PANORAMA GERAL ESTADUAL
    cells.append(make_cell("markdown", """## 1. Panorama Geral Estadual: Dinamica Anual de Queimadas (1985 a 2026)

O grafico abaixo apresenta a soma anual da area queimada no conjunto das 29 Unidades de Conservacao. A linha tracejada corresponde a media movel centrada de 5 anos para atenuacao da variabilidade interanual. As anotacoes apontam os anos com maior extensao territorial queimada, associados a fenomenos climaticos de seca severa como os eventos de El Nino.
"""))

    cells.append(make_cell("code", """fig, ax = plot_panorama_estadual(df_series, figsize=(13, 5.5))
plt.show()
"""))

    # 8. MATRIZ DE CALOR POR GERENCIA
    cells.append(make_cell("markdown", """### Matriz de Intensidade Temporal por Gerencia Regional

A distribuicao matricial abaixo indica a taxa media anual de queima (percentual da area da gerencia atingida) por ano e por regional administrativa do IDEFLOR-Bio.
"""))

    cells.append(make_cell("code", """# Construcao da matriz pivoteada de taxa media anual por gerencia
pivot_gerencia = df_series.pivot_table(
    index="gerencia",
    columns="ano",
    values="taxa_queimada_pct",
    aggfunc="mean"
)

plt.figure(figsize=(15, 6))
sns.heatmap(
    pivot_gerencia,
    cmap="YlOrRd",
    linewidths=0.5,
    cbar_kws={"label": "Taxa Media de Queima (% da UC)"}
)
plt.title("Intensidade Anual de Queimadas por Gerencia Regional do IDEFLOR-Bio", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("Ano", fontsize=10, fontweight="bold")
plt.ylabel("Gerencia Regional", fontsize=10, fontweight="bold")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
"""))

    # 8.1 MATRIZ DE CALOR POR UNIDADE DE CONSERVACAO (AGRUPADAS POR GERENCIA)
    cells.append(make_cell("markdown", """### Matriz de Intensidade Temporal por Unidade de Conservacao

Distribuicao analitica da taxa anual de queima (% da area da UC) para cada uma das 29 Unidades de Conservacao Estaduais de 1985 a 2026, agrupadas por sua respectiva Gerencia Regional.
"""))

    cells.append(make_cell("code", """# Matriz de calor completa com todas as 29 UCs agrupadas por Gerencia Regional
fig, ax = plot_matriz_intensidade_unidades(df_series, figsize=(18, 11))
plt.show()
"""))

    cells.append(make_cell("markdown", """### Filtro da Matriz por Gerencia Regional Especifica

O seletor abaixo permite inspecionar a matriz temporal das Unidades de Conservacao de forma individualizada para cada Gerencia Regional.
"""))

    cells.append(make_cell("code", """# Seletor interativo da matriz por Gerencia Regional com saida estavel
gerencias_opcoes = ["TODAS"] + sorted([g for g in df_series["gerencia"].dropna().unique() if g])

dropdown_ger_matriz = widgets.Dropdown(
    options=gerencias_opcoes,
    value="TODAS",
    description="Gerência:",
    layout=widgets.Layout(width="550px")
)

out_matriz = widgets.Output()

def atualizar_matriz_gerencia(change=None):
    gerencia_sel = dropdown_ger_matriz.value
    with out_matriz:
        clear_output(wait=True)
        fig, ax = plot_matriz_intensidade_unidades(df_series, gerencia_filtro=gerencia_sel)
        plt.show()

dropdown_ger_matriz.observe(atualizar_matriz_gerencia, names="value")
display(dropdown_ger_matriz, out_matriz)
atualizar_matriz_gerencia()
"""))

    # 9. ANALISE COMPARATIVA: PROTECAO INTEGRAL VS USO SUSTENTAVEL
    cells.append(make_cell("markdown", """## 2. Regime de Fogo por Categoria e Grupo SNUC

Comparativo do comportamento historico do fogo entre Unidades de Protecao Integral e Unidades de Uso Sustentavel, avaliando o grau de vulnerabilidade de cada modelo de gestao.
"""))

    cells.append(make_cell("code", """df_grupo_ano = df_series.groupby(["ano", "grupo"]).agg(
    area_queimada_ha=("burned_ha", "sum"),
    area_total_ha=("area_uc_ha", "sum")
).reset_index()

df_grupo_ano["taxa_queimada_pct"] = (df_grupo_ano["area_queimada_ha"] / df_grupo_ano["area_total_ha"]) * 100

plt.figure(figsize=(13, 5))
sns.lineplot(
    data=df_grupo_ano,
    x="ano",
    y="taxa_queimada_pct",
    hue="grupo",
    palette={"Proteção Integral": "#1E3A8A", "Uso Sustentável": "#D97706"},
    linewidth=2.2
)
plt.title("Evolucao da Taxa Anual de Queima por Grupo do SNUC", fontsize=12, fontweight="bold", pad=12)
plt.xlabel("Ano", fontsize=10, fontweight="bold")
plt.ylabel("Taxa de Queima Ponderada (%)", fontsize=10, fontweight="bold")
plt.grid(True, linestyle=":", alpha=0.6)
plt.tight_layout()
plt.show()
"""))

    # 10. AVALIACAO DO MARCO LEGAL
    cells.append(make_cell("markdown", """## 3. Avaliacao do Marco Legal de Criacao das Unidades de Conservacao

Verificacao do comportamento da taxa de queima territorial nos periodos anterior e posterior ao decreto de criacao de cada unidade. O seletor abaixo permite inspecionar cada uma das 29 UCs individualmente.
"""))

    cells.append(make_cell("code", """# Seletor interativo para inspecao de cada UC
ucs_validas = sorted(df_series["uc_id"].unique())
nomes_map = dict(zip(df_meta["id"], df_meta["nome"]))

dropdown_uc = widgets.Dropdown(
    options=[(f"{uid} - {nomes_map.get(uid, f'UC {uid}')}", uid) for uid in ucs_validas],
    value=8,
    description="UC:",
    layout=widgets.Layout(width="500px")
)

def atualizar_grafico_uc(uc_id):
    fig, ax = plot_uc_before_after(df_series, uc_id=uc_id, figsize=(12, 4.5))
    plt.show()
    
    # Exibir metricas sinteticas
    sub = df_series[df_series["uc_id"] == uc_id]
    nome = sub["uc_nome"].iloc[0]
    ano_cria = sub["ano_criacao"].iloc[0]
    pre = sub[sub["status_marco"] == "Pré-Criação"]["taxa_queimada_pct"].mean()
    pos = sub[sub["status_marco"] == "Pós-Criação"]["taxa_queimada_pct"].mean()
    
    print(f"Unidade: {nome} (Decreto: {ano_cria if pd.notna(ano_cria) else 'Nao informado'})")
    if pd.notna(pre) and not np.isnan(pre):
        print(f"Taxa Media Pre-Criacao: {pre:.2f}% ao ano | Taxa Media Pos-Criacao: {pos:.2f}% ao ano")
        dif = pos - pre
        sinal = "+" if dif > 0 else ""
        print(f"Variacao Liquida Pos-Decreto: {sinal}{dif:.2f} pontos percentuais")
    else:
        print(f"Taxa Media Pos-Criacao: {pos:.2f}% ao ano (sem serie pre-criacao anterior a 1985)")
    print("=" * 70)

widgets.interact(atualizar_grafico_uc, uc_id=dropdown_uc)
"""))

    # 11. MAPEAMENTO CARTOGRAFICO
    cells.append(make_cell("markdown", """## 4. Mapeamento Cartografico da Pressao Historica de Queimadas

Espacializacao geografica das 29 Unidades de Conservacao classificadas pela taxa media anual de queima registrada entre 1985 e 2026.
"""))

    cells.append(make_cell("code", """# Prancha cartografica oficial da media historica (1985 a 2026)
fig, ax = plot_static_map(df_series, figsize=(16, 11))
plt.show()
"""))

    cells.append(make_cell("markdown", """### Prancha Cartográfica Temática Interativa por Ano Específico

Selecione qualquer ano da série temporal (1985 a 2026) na lista suspensa abaixo para gerar e visualizar a prancha temática estática oficial do NGEO / IDEFLOR-Bio correspondente.
"""))

    cells.append(make_cell("code", """# Seletor e acionador da prancha cartografica tematica por ano
anos_disponiveis = sorted(df_series["ano"].unique(), reverse=True)

dropdown_ano = widgets.Dropdown(
    options=anos_disponiveis,
    value=int(df_series["ano"].max()),
    description="Ano:",
    layout=widgets.Layout(width="280px")
)

btn_gerar_mapa = widgets.Button(
    description="Gerar Prancha do Ano",
    button_style="primary",
    icon="map",
    layout=widgets.Layout(width="220px")
)

out_mapa_ano = widgets.Output()

def ao_clicar_gerar_mapa(b):
    ano_escolhido = dropdown_ano.value
    with out_mapa_ano:
        clear_output(wait=True)
        print(f"Gerando prancha cartografica tematica para o ano de {ano_escolhido}...")
        fig_ano, ax_ano = plot_static_map(df_series, ano=ano_escolhido, figsize=(16, 11))
        plt.show()

btn_gerar_mapa.on_click(ao_clicar_gerar_mapa)

controles_mapa = widgets.HBox(
    [dropdown_ano, btn_gerar_mapa],
    layout=widgets.Layout(align_items="center", gap="12px", margin="0 0 14px 0")
)
display(controles_mapa, out_mapa_ano)

# Renderizacao inicial do ano mais recente
ao_clicar_gerar_mapa(None)
"""))

    cells.append(make_cell("markdown", """### Mini Dashboard Analítico Interativo (MapLibre GL JS)

Painel analítico vetorial interativo desenvolvido com MapLibre GL JS e estilização cartográfica escura moderna (*glassmorphism*), sem dependência de chaves de API. Disponibiliza filtros dinâmicos por Gerência Regional e Grupo SNUC com recálculo automático em tempo real de indicadores consolidados (área protegida filtrada, taxa média do grupo e contagem de UCs), além de módulo lateral deslizante de inspeção detalhada com gráficos da série histórica (1985–2026) e avaliação do marco legal de criação ao clicar em qualquer Unidade de Conservação.
"""))

    cells.append(make_cell("code", """# Geração e exibição do Mini Dashboard interativo MapLibre GL JS diretamente na célula
display(display_maplibre_in_notebook(df_series, height=720))
"""))

    # 12. SINTESE CONCLUSIVA
    cells.append(make_cell("markdown", """## 5. Sintese dos Resultados

1. **Concentracao Espacial:** A pressao de fogo concentra-se predominantemente na Gerencia Regional do Xingu (GRX), impulsionada pela APA Triunfo do Xingu, e na Gerencia Regional do Araguaia (GRA).
2. **Eficacia Diferenciada dos Decretos:** Unidades de Protecao Integral evidenciam queda acentuada na taxa de queima apos o decreto legal de criacao. Em contraste, Unidades de Uso Sustentavel de grande extensao territorial continuam sujeitas a dinamicidade de fronteira agricola e queimas pastoris recorrentes.
3. **Eventos Climaticos Extremos:** Os anos de maior extensao territorial queimada coincidem com episodios severos de El Nino e anomalias termicas do Atlantico Tropical Norte.
"""))

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.10.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)

    print(f"Notebook atualizado com sucesso em: {NOTEBOOK_PATH}")

if __name__ == "__main__":
    build_notebook()

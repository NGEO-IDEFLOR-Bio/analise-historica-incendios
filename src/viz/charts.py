"""
Funções de visualização em padrão de excelência editorial (R / ggplot2 / FT).
Panorama Geral, Por Gerência Regional e Por Unidade de Conservação.
"""
from typing import Optional, List, Dict, Any
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns

from src.viz.theme import (
    apply_ggplot_theme,
    COLOR_FIRE_MAIN,
    COLOR_FIRE_LIGHT,
    COLOR_PRE_CREATION,
    COLOR_POST_CREATION,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_GRID
)
from src.config import SIGLAS_GERENCIAS

def plot_panorama_estadual(df: pd.DataFrame, figsize=(12, 6)):
    """
    Gráfico 1: Panorama Geral Estadual (1985-2023)
    Área total queimada anual em todas as 29 UCs, com linha de tendência e destaques de anos críticos.
    """
    apply_ggplot_theme()
    fig, ax = plt.subplots(figsize=figsize)

    # Agrupa área queimada estadual por ano
    df_ano = df.groupby("ano")["burned_ha"].sum().reset_index()
    df_ano["burned_mil_ha"] = df_ano["burned_ha"] / 1000.0  # Em mil hectares
    df_ano["media_movel_5a"] = df_ano["burned_mil_ha"].rolling(window=5, min_periods=1, center=True).mean()

    # Preenchimento e barras sutis
    ax.fill_between(df_ano["ano"], df_ano["burned_mil_ha"], color=COLOR_FIRE_LIGHT, alpha=0.35)
    ax.plot(df_ano["ano"], df_ano["burned_mil_ha"], color=COLOR_FIRE_MAIN, linewidth=2.0, marker="o", markersize=4, label="Área Queimada Anual")
    ax.plot(df_ano["ano"], df_ano["media_movel_5a"], color="#2B2D42", linewidth=2.2, linestyle="--", label="Tendência (Média Móvel 5 Anos)")

    # Identificar e destacar os 3 anos com maiores picos
    top3 = df_ano.nlargest(3, "burned_mil_ha")
    for _, row in top3.iterrows():
        ax.scatter(row["ano"], row["burned_mil_ha"], color="#900C3F", s=60, zorder=5)
        ax.annotate(
            f"{int(row['ano'])}\n{row['burned_mil_ha']:,.0f} mil ha",
            xy=(row["ano"], row["burned_mil_ha"]),
            xytext=(0, 12),
            textcoords="offset points",
            ha="center",
            fontsize=8.5,
            fontweight="bold",
            color="#900C3F",
            arrowprops=dict(arrowstyle="->", color="#900C3F", lw=0.8)
        )

    # Títulos e formatação
    ax.set_title("Evolucao Historica da Area Queimada nas 29 UCs do Para (1985 a 2023)", fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Área Queimada Anual (mil hectares)", fontsize=10, labelpad=10)
    ax.set_xlabel("Ano", fontsize=10, labelpad=8)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax.set_xlim(1984, 2024)
    ax.legend(loc="upper left")

    # Nota de rodapé técnica
    plt.figtext(
        0.12, -0.02,
        "Fonte: MapBiomas Fogo (Coleção 3 - Landsat 30m). Processamento via Google Earth Engine sobre shapes oficiais do IDEFLOR-Bio.",
        fontsize=8, color=COLOR_TEXT_MUTED
    )
    plt.tight_layout()
    return fig, ax

def plot_comparativo_gerencias(df: pd.DataFrame, figsize=(14, 7)):
    """
    Gráfico 2: Comparativo entre Gerências Regionais
    Normalizado: Taxa Média Anual de Queima (% do Território Atingido) por Gerência.
    """
    apply_ggplot_theme()
    fig, ax = plt.subplots(figsize=figsize)

    df_copia = df.copy()
    df_copia["sigla_gerencia"] = df_copia["gerencia"].map(SIGLAS_GERENCIAS).fillna(df_copia["gerencia"])

    # Agrupar por gerência e calcular métricas consolidadas
    ger_resumo = df_copia.groupby(["sigla_gerencia"]).agg(
        area_total_ha=("area_uc_ha", "first"),
        taxa_media_pct=("taxa_queimada_pct", "mean"),
        taxa_max_pct=("taxa_queimada_pct", "max"),
        burned_ha_total=("burned_ha", "sum")
    ).reset_index().sort_values(by="taxa_media_pct", ascending=True)

    y_pos = np.arange(len(ger_resumo))
    bars = ax.barh(y_pos, ger_resumo["taxa_media_pct"], color=COLOR_FIRE_MAIN, height=0.55, alpha=0.85)

    # Valores na ponta das barras
    for bar, (_, row) in zip(bars, ger_resumo.iterrows()):
        ax.text(
            bar.get_width() + 0.05,
            bar.get_y() + bar.get_height() / 2,
            f"{row['taxa_media_pct']:.2f}% / ano (Pico: {row['taxa_max_pct']:.1f}%)",
            va="center",
            ha="left",
            fontsize=8.5,
            color=COLOR_TEXT_MAIN
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(ger_resumo["sigla_gerencia"], fontsize=9.5, fontweight="medium")
    ax.set_title("Pressão Média de Fogo por Gerência Regional (Normalizada por Área)", fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Taxa Média de Queima (% da área da Gerência queimada ao ano, 1985-2023)", fontsize=10, labelpad=8)
    ax.set_xlim(0, max(ger_resumo["taxa_media_pct"]) * 1.45)

    plt.figtext(
        0.12, -0.02,
        "A normalização por área percentual permite comparar com justiça gerências de escalas distintas (ex: Belém vs. Calha Norte).",
        fontsize=8, color=COLOR_TEXT_MUTED
    )
    plt.tight_layout()
    return fig, ax

def plot_uc_before_after(df: pd.DataFrame, uc_id: int, figsize=(12, 6)):
    """
    Gráfico 3: Análise Causal / Marco de Criação de uma UC
    Compara a taxa de queima antes e depois do decreto de criação, com linhas de médias.
    """
    apply_ggplot_theme()
    fig, ax = plt.subplots(figsize=figsize)

    df_uc = df[df["uc_id"] == uc_id].sort_values(by="ano").copy()
    if df_uc.empty:
        raise ValueError(f"UC ID {uc_id} não encontrada no dataset.")

    uc_nome = df_uc["uc_nome"].iloc[0]
    ano_criacao = df_uc["ano_criacao"].iloc[0]
    gerencia = df_uc["gerencia"].iloc[0]
    area_ha = df_uc["area_uc_ha"].iloc[0]

    pre_mask = df_uc["ano"] < ano_criacao
    pos_mask = df_uc["ano"] >= ano_criacao

    media_pre = df_uc.loc[pre_mask, "taxa_queimada_pct"].mean() if pre_mask.any() else 0.0
    media_pos = df_uc.loc[pos_mask, "taxa_queimada_pct"].mean() if pos_mask.any() else 0.0

    # Shading do período pré e pós
    ax.axvspan(df_uc["ano"].min(), ano_criacao, color="#ECEFF1", alpha=0.5, label="Período Pré-Criação")
    ax.axvspan(ano_criacao, df_uc["ano"].max(), color="#FFF3E0", alpha=0.45, label="Período Pós-Criação")

    # Linha da taxa de queima
    ax.plot(df_uc["ano"], df_uc["taxa_queimada_pct"], color=COLOR_FIRE_MAIN, linewidth=2.0, marker="o", markersize=4)

    # Linhas horizontais das médias
    if pre_mask.any():
        ax.hlines(media_pre, df_uc["ano"].min(), ano_criacao, colors=COLOR_PRE_CREATION, linestyles="--", linewidth=1.8, label=f"Média Pré-Criação ({media_pre:.2f}%)")
    if pos_mask.any():
        ax.hlines(media_pos, ano_criacao, df_uc["ano"].max(), colors="#E65100", linestyles="--", linewidth=1.8, label=f"Média Pós-Criação ({media_pos:.2f}%)")

    # Linha vertical do Marco de Criação
    ax.axvline(ano_criacao, color="#1B5E20", linestyle="-", linewidth=2.2)
    ax.text(
        ano_criacao + 0.4,
        ax.get_ylim()[1] * 0.88 if ax.get_ylim()[1] > 0 else 1.0,
        f"Marco Legal: Criação ({int(ano_criacao)})",
        color="#1B5E20",
        fontweight="bold",
        fontsize=9.5,
        rotation=0,
        bbox=dict(boxstyle="round,pad=0.3", fc="#E8F5E9", ec="#1B5E20", lw=1)
    )

    # Títulos e labels
    ax.set_title(f"Impacto do Marco de Criação no Regime de Fogo: {uc_nome}", fontsize=13, fontweight="bold", pad=15)
    ax.set_subtitle = f"{gerencia} | Área: {area_ha:,.0f} ha | Decreto: {int(ano_criacao)}"
    ax.set_ylabel("Taxa Anual de Queima (% da área da UC)", fontsize=10, labelpad=8)
    ax.set_xlabel("Ano", fontsize=10, labelpad=8)
    ax.legend(loc="upper left")

    plt.tight_layout()
    return fig, ax

def plot_matriz_intensidade_unidades(
    df: pd.DataFrame,
    gerencia_filtro: Optional[str] = None,
    figsize=(18, 11)
):
    """
    Matriz de Intensidade Temporal por Unidade de Conservacao (agrupadas por Gerencia Regional).
    Permite visualizar a taxa anual de queima (% da UC) de 1985 a 2026 para cada uma das UCs.
    """
    apply_ggplot_theme()
    
    df_plot = df.copy()
    if gerencia_filtro and gerencia_filtro != "TODAS":
        df_plot = df_plot[df_plot["gerencia"].str.contains(gerencia_filtro, regex=False, na=False)]
    
    df_plot["sigla_ger"] = df_plot["gerencia"].map(SIGLAS_GERENCIAS).fillna(df_plot["gerencia"])
    df_plot["uc_label"] = "[" + df_plot["sigla_ger"] + "] " + df_plot["uc_nome"]
    
    ordem_ucs = df_plot[["uc_label", "sigla_ger", "uc_nome"]].drop_duplicates().sort_values(["sigla_ger", "uc_nome"])["uc_label"].tolist()
    
    pivot_ucs = df_plot.pivot_table(
        index="uc_label",
        columns="ano",
        values="taxa_queimada_pct",
        aggfunc="first"
    ).reindex(ordem_ucs).fillna(0.0)
    
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        pivot_ucs,
        cmap="YlOrRd",
        linewidths=0.3,
        linecolor="#CBD5E1",
        cbar_kws={"label": "Taxa Anual de Queima (% da UC)", "shrink": 0.75},
        ax=ax
    )
    
    titulo = "Matriz de Intensidade Temporal por Unidade de Conservacao (1985 a 2026)"
    if gerencia_filtro and gerencia_filtro != "TODAS":
        titulo += f" - {gerencia_filtro}"
        
    ax.set_title(titulo, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Ano", fontsize=10, fontweight="bold")
    ax.set_ylabel("Unidade de Conservacao (agrupada por Gerencia)", fontsize=10, fontweight="bold")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, fontsize=8.5)
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=8.5)
    
    plt.tight_layout()
    return fig, ax

"""
Módulo de visualização e temas inspirados no ecossistema R (ggplot2, hrbrthemes, cowplot).
"""
import matplotlib.pyplot as plt
import seaborn as sns

# Paletas de cores semânticas (padrão publicação / alta legibilidade)
PALETTE_FIRE = ["#FFE0B2", "#FFB74D", "#FF7043", "#F4511E", "#D84315", "#BF360C"]
COLOR_FIRE_MAIN = "#D84315"       # Laranja/vermelho queimada escuro
COLOR_FIRE_LIGHT = "#FFAB91"      # Tom suave de apoio
COLOR_CONSERVED = "#1B5E20"       # Verde conservação profundo
COLOR_PRE_CREATION = "#78909C"    # Cinza azulado (período anterior)
COLOR_POST_CREATION = "#E65100"   # Laranja terracota (período posterior)
COLOR_GRID = "#E5E7EB"            # Cinza muito claro para grid sutil
COLOR_TEXT_MAIN = "#111827"       # Quase preto para títulos
COLOR_TEXT_MUTED = "#6B7280"      # Cinza para subtítulos e notas

def apply_ggplot_theme():
    """Aplica estilo visual minimalista e elegante inspirado em ggplot2 / hrbrthemes."""
    plt.rcParams.update({
        # Fontes e texto
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial"],
        "text.color": COLOR_TEXT_MAIN,
        "axes.labelcolor": COLOR_TEXT_MAIN,
        "xtick.color": COLOR_TEXT_MUTED,
        "ytick.color": COLOR_TEXT_MUTED,
        
        # Eixos e bordas (remover poluição visual)
        "axes.edgecolor": "#D1D5DB",
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        
        # Grid
        "axes.grid": True,
        "grid.color": COLOR_GRID,
        "grid.linestyle": "--",
        "grid.linewidth": 0.6,
        "grid.alpha": 0.8,
        
        # Fundo
        "axes.facecolor": "#FFFFFF",
        "figure.facecolor": "#FFFFFF",
        
        # Legendas
        "legend.frameon": False,
        "legend.fontsize": 9,
        "legend.title_fontsize": 10,
        
        # Resolução e proporções
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": None
    })

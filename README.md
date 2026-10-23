# Analise Historica de Incendios nas Unidades de Conservacao do Para (IDEFLOR-Bio)
### Serie Temporal Integrada de Cicatrizes de Queimada (1985 a 2026) | MapBiomas Fogo & MODIS GEE

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/NGEO-IDEFLOR-Bio/analise-historica-incendios/blob/main/notebooks/01_analise_historica_incendios.ipynb)

Repositorio tecnico oficial destinado ao mapeamento espaco-temporal de cicatrizes de queimada nas 29 Unidades de Conservacao Estaduais geridas pelo Instituto de Desenvolvimento Florestal e da Biodiversidade do Estado do Para (IDEFLOR-Bio). 

O escopo do projeto contempla a avaliacao da serie temporal integrada de 1985 a 2026 (42 anos ininterruptos), mensurando a dinamica interanual, a variabilidade espacial entre Gerencias Regionais, as assimetrias entre categorias do SNUC e a eficacia dos decretos legais de criacao sobre o regime historico de fogo.

---

## Objetivos Metodologicos

1. **Integracao Temporal Multissensorial (1985 a 2026):**
   * **1985 a 2023:** Serie historica de 30 metros de resolucao espacial do MapBiomas Fogo (Colecao 3), baseada em sensores Landsat.
   * **2024 a 2026:** Monitoramento continuo de cicatrizes mensais do produto MODIS MCD64A1 (Colecao 6.1, resolucao de 500 metros) processado diretamente via Google Earth Engine.
2. **Normalizacao Territorial por Area:**
   * Calculo da taxa anual percentual de queima em relacao a area total de cada poligono cadastral oficial, permitindo comparacoes tecnicamente consistentes entre unidades com dimensoes territoriais contrastantes (de 1.397 ha a 4.534.900 ha).
3. **Estratificacao Regional e Institucional:**
   * Agrupamento analitico pelas 9 Gerencias Regionais do IDEFLOR-Bio (GRCN-I, GRCN-II, GRCN-III, GRB, GRTUC, GRA, GRM, GRNE, GRX).
   * Segregacao por grupos de manejo do Sistema Nacional de Unidades de Conservacao (SNUC: Protecao Integral versus Uso Sustentavel).
4. **Avaliacao do Efeito do Marco Legal:**
   * Analise empirica do tipo antes e depois da data oficial do decreto de criacao territorial de cada unidade, verificando se a oficializacao legal resultou em contencao efetiva da taxa de queima territorial.
5. **Difusao Cartografica e Visual:**
   * Pranchas tematicas estaticas oficiais prontas para publicacao tecnica com seletor de ano sob demanda.
   * Mini Dashboard analitico interativo sem dependencia de chaves pagas, com visualizacao regional, modo de analise por unidade, sobreposicao de cicatrizes reais em tiles e abertura direta em nova aba.

---

## Estrutura do Repositorio

```text
analise-historica-incendios/
├── data/
│   ├── raw/                  # Geometrias vetoriais oficiais das 29 UCs e limites contextuais
│   ├── processed/            # Series temporais anuais integradas (1985 a 2026) e metadados tabulares
│   └── output/               # Pranchas estaticas geradas e aplicacao web interativa (HTML)
├── docs/
│   └── catalogo_ucs.md       # Catalogo cadastral das 29 UCs, gerencias, categorias e datas de criacao
├── notebooks/
│   └── 01_analise_historica_incendios.ipynb # Notebook oficial interativo (executavel no Google Colab e Jupyter)
├── scripts/
│   ├── build_notebook.py     # Script gerador e sincronizador do notebook executivo
│   ├── generate_interactive_map.py # Gerador do painel web Leaflet institucional
│   └── setup_and_validate.py # Validacao topologica das geometrias e metadados cadastrais
├── src/
│   ├── config.py             # Definicoes de caminhos, constantes de CRS e parametros operacionais
│   ├── gee_auth.py           # Conexao universal e adaptativa com Google Earth Engine (Colab e local)
│   ├── ucs.py                # Camada cadastral e relacoes espaciais das unidades de conservacao
│   ├── extractors/
│   │   ├── mapbiomas_fogo.py # Extracao de cicatrizes MapBiomas Fogo Colecao 3 (1985 a 2023)
│   │   └── modis_burned_area.py # Extracao de cicatrizes mensais MODIS MCD64A1 via GEE (2024 a 2026)
│   └── viz/
│       ├── charts.py         # Graficos comparativos, series temporais e matrizes de calor
│       ├── maps.py           # Pranchas cartograficas tematicas estaticas e wrapper notebook
│       ├── leaflet_dashboard.py # Painel analitico interativo moderno com isolamento de visao
│       └── theme.py          # Padronizacao tipografica e paleta de cores institucional
├── pyproject.toml
└── README.md
```

---

## Sintese Territorial das Gerencias Regionais

O banco de dados geoespacial integra 29 poligonos oficiais distribuidos em 9 Gerencias Regionais:

| Gerencia Regional | Sigla | Quantidade de UCs | Area Total (ha) | Proporcao Territorial | Periodo de Criacao |
| :--- | :---: | :---: | ---: | :---: | :---: |
| Calha Norte II | GRCN-II | 5 | 7.149.079 ha | 35.8% | 2006 a 2024 |
| Calha Norte III | GRCN-III | 2 | 5.334.536 ha | 26.7% | 2006 |
| Marajo | GRM | 2 | 4.600.124 ha | 23.1% | 1989 a 2010 |
| Xingu | GRX | 5 | 2.178.749 ha | 10.9% | 2006 a 2021 |
| Tucurui | GRTUC | 3 | 550.047 ha | 2.8% | 1997 a 2002 |
| Calha Norte I | GRCN-I | 2 | 60.980 ha | 0.3% | 2001 |
| Araguaia | GRA | 2 | 51.864 ha | 0.3% | 1996 |
| Belem | GRB | 4 | 15.007 ha | 0.1% | 1993 a 2010 |
| Nordeste | GRNE | 4 | 10.312 ha | 0.1% | 1990 a 2018 |
| **Total** | **-** | **29** | **19.950.698 ha** | **100.0%** | **1989 a 2024** |

---

## Metricas e Formulacao de Normalizacao

Para assegurar comparabilidade tecnica entre unidades de conservacao de portes heterogeneos, aplicam-se as seguintes formulacoes matematicas:

### 1. Taxa Percentual Anual de Queima

Mede a proporcao da area da Unidade de Conservacao atingida pelo fogo em determinado ano:

```math
\text{Taxa Anual (\%)} = \left(\frac{\text{Área Queimada Anual no Polígono (ha)}}{\text{Área Cadastral Total do Polígono (ha)}}\right) \times 100
```

### 2. Avaliacao do Efeito do Marco Legal

Compara o comportamento medio da taxa de queima territorial antes e apos o decreto oficial de criacao:

* **Variacao Absoluta (em pontos percentuais):**

```math
\Delta_{\text{abs}} = \overline{\text{Taxa}}_{\text{Pós-Criação}} - \overline{\text{Taxa}}_{\text{Pré-Criação}}
```

* **Variacao Relativa (%):**

```math
\Delta_{\text{rel}} = \left(\frac{\overline{\text{Taxa}}_{\text{Pós-Criação}} - \overline{\text{Taxa}}_{\text{Pré-Criação}}}{\overline{\text{Taxa}}_{\text{Pré-Criação}}}\right) \times 100
```

---

## Fontes de Dados e Assets Utilizados

* **MapBiomas Fogo (Colecao 3):** Cobertura anual de cicatrizes de fogo para o Brasil (1985 a 2023), baseada em series Landsat (resolucao de 30 metros), asset oficial GEE `projects/mapbiomas-public/assets/brazil/fire/collection3/mapbiomas_fire_collection3_annual_burned_coverage_v1`.
* **MODIS MCD64A1 (Colecao 6.1):** Produto global de cicatrizes de queima mensais (resolucao de 500 metros), asset oficial GEE `MODIS/061/MCD64A1`.
* **Limites Territoriais Oficiais:** Base vetorial em formato GeoJSON fornecida pelo IDEFLOR-Bio, padronizada no datum SIRGAS 2000 (EPSG:4674) e convertida para WGS 84 (EPSG:4326) em visualizacoes web.

---

## Instrucoes de Execucao

### 1. Execucao Direta no Google Colab (Recomendada)
Basta clicar no selo **Open in Colab** no topo deste documento. O notebook executara com suporte a:
* **Execucao Imediata:** A base historica completa (1985 a 2026) ja vem inclusa em `data/processed/`, permitindo rodar todos os graficos, matrizes, mapas e o dashboard sem necessidade obrigatoria de conexao com o Earth Engine.
* **Conexao Opcional com Google Earth Engine:** Caso deseje reprocessar ou extrair novas cicatrizes, basta preencher a variavel `GEE_PROJECT` na celula 4 com o ID do seu Google Cloud Project (ex: `GEE_PROJECT = "ee-seu-usuario"`).

### 2. Execucao em Ambiente Local

1. Clonar o repositorio e preparar o ambiente virtual:
```bash
git clone https://github.com/NGEO-IDEFLOR-Bio/analise-historica-incendios.git
cd analise-historica-incendios
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
pip install -e .
```

2. (Opcional) Configurar credenciais do Google Earth Engine para extracoes locais:
Copiar `.env.example` para `.env` e indicar a chave de Service Account ou autenticar interativamente via terminal com `earthengine authenticate`.

3. Executar o notebook:
```bash
jupyter lab notebooks/01_analise_historica_incendios.ipynb
```

---

## Funcionalidades do Notebook

1. **Panorama Estadual e Serie Historica (1985 a 2026):** Evolucao anual de area absoluta queimada e taxa percentual ponderada para o conjunto das 29 UCs estaduais.
2. **Comparativo Normalizado por Gerencia Regional:** Diagramas de dispersao e boxplots da taxa percentual anual entre as 9 gerencias.
3. **Matriz de Calor Temporal por Unidade de Conservacao:** Painel matricial completo das 29 UCs agrupadas por Gerencia Regional e filtro interativo estavel (sem trepidacao de tela) para inspecao de cada gerencia isoladamente.
4. **Regime de Fogo por Categoria e Grupo SNUC:** Analise temporal comparativa entre Protecao Integral e Uso Sustentavel.
5. **Avaliacao do Marco Legal de Criacao:** Inspecao dinamica por Unidade de Conservacao confrontando as taxas medias antes e depois da data oficial do decreto.
6. **Prancha Cartografica Tematica Oficial por Ano:** Geracao estatica em alta definicao da classificacao espacial de queima das 29 UCs com seletor de ano e botao de execucao dedicado.
7. **Mini Dashboard Analitico Interativo:** Painel web vetorial com alternancia entre Visao Regional e Analise por Unidade, zoom inteligente sincronizado, camadas de cicatrizes reais (MapBiomas Fogo e MODIS MCD64A1) e botao para abertura em tela cheia via nova aba.

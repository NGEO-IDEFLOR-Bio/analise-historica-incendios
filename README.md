# Analise Historica de Incendios nas Unidades de Conservacao do Para (IDEFLOR-Bio)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/NGEO-IDEFLOR-Bio/analise-historica-incendios/blob/main/notebooks/01_analise_historica_incendios.ipynb)

Repositorio tecnico destinado ao mapeamento espaco-temporal de cicatrizes de queimada e focos de calor nas 29 Unidades de Conservacao Estaduais geridas pelo Instituto de Desenvolvimento Florestal e da Biodiversidade do Estado do Para (IDEFLOR-Bio). O escopo do projeto contempla a avaliacao da serie temporal de 1985 a 2023, mensurando o efeito dos decretos de criacao territorial sobre o regime historico de fogo.

## Objetivos Metodologicos

1. Consolidacao da serie temporal anual de cicatrizes de fogo (1985 a 2023) obtida via Google Earth Engine a partir do MapBiomas Fogo (Colecao 3, resolucao de 30 metros).
2. Normalizacao territorial das metricas de fogo mediante calculo da taxa anual percentual de queima relativa a area total de cada poligono oficial.
3. Agrupamento regional por Gerencia Regional e por Grupo de Manejo do Sistema Nacional de Unidades de Conservacao (SNUC: Protecao Integral versus Uso Sustentavel).
4. Analise de impacto causal do tipo antes e depois do marco legal de criacao territorial.

## Estrutura do Repositorio

```text
analise-historica-incendios/
├── data/
│   ├── raw/                  # Geometrias originais das UCs (GeoJSON SIRGAS 2000, EPSG:4674)
│   ├── processed/            # Tabelas consolidadas de metadados e series temporais (CSV e JSON)
│   └── output/               # Mapas cartograficos, graficos gerados e exportacoes HTML
├── docs/
│   └── catalogo_ucs.md       # Catalogo cadastral das 29 UCs, gerencias, areas e datas legais
├── notebooks/
│   └── 01_analise_historica_incendios.ipynb # Caderno interativo com graficos e mapas
├── scripts/
│   ├── build_notebook.py     # Script gerador do notebook executivo
│   └── setup_and_validate.py # Validacao das geometrias e geracao de catalogos tabulares
├── src/
│   ├── config.py             # Definicoes de caminhos, constantes de CRS e parametros
│   ├── gee_auth.py           # Autenticacao no Google Earth Engine via Service Account
│   ├── ucs.py                # Camada de consulta cadastral e espacial das unidades
│   ├── extractors/
│   │   └── mapbiomas_fogo.py # Extrator de cicatrizes de fogo no GEE (1985 a 2023)
│   └── viz/
│       ├── charts.py         # Graficos comparativos e analise temporal
│       ├── maps.py           # Geracao de mapas coropleticos estaticos e interativos
│       └── theme.py          # Padronizacao tipografica e paleta de cores
├── tests/
│   └── test_ucs.py           # Testes de integridade cadastral e topologica
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## Sintese Territorial

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
| Total | - | 29 | 19.950.698 ha | 100.0% | 1989 a 2024 |

## Metricas e Normalizacao

Para assegurar comparabilidade entre unidades com ordens de grandeza distintas (de 1.397 hectares a 4.534.900 hectares), adotam-se as seguintes formulacoes:

1. Taxa Percentual Anual de Queima:
   Taxa (%) = (Area Queimada Anual no Poligono em ha / Area Total do Poligono em ha) * 100

2. Avaliacao do Marco Temporal Legal:
   Variacao Absoluta (pontos percentuais) = Media Pos Criacao (%) - Media Pre Criacao (%)
   Variacao Relativa (%) = ((Media Pos Criacao - Media Pre Criacao) / Media Pre Criacao) * 100

## Fonte de Dados

- MapBiomas Fogo (Colecao 3): Cobertura anual de cicatrizes de fogo para o Brasil (1985 a 2023), baseada em series temporais Landsat (resolucao espacial de 30 metros), processada diretamente via Google Earth Engine no asset `projects/mapbiomas-public/assets/brazil/fire/collection3/mapbiomas_fire_collection3_annual_burned_coverage_v1`.
- Limites Territoriais Oficiais: Base vetorial fornecida pelo IDEFLOR-Bio no sistema geocartografico SIRGAS 2000 (EPSG:4674).

## Instalacao e Execucao

1. Clonar o repositorio e instalar dependencias:
```bash
git clone https://github.com/NGEO-IDEFLOR-Bio/analise-historica-incendios.git
cd analise-historica-incendios
pip install -e .
```

2. Configurar credenciais de acesso:
Copiar `.env.example` para `.env` e inserir a chave de conta de servico do Google Cloud Platform com permissao no Google Earth Engine.

3. Executar o pipeline de processamento:
```bash
python scripts/setup_and_validate.py
python src/extractors/mapbiomas_fogo.py
```

4. Abrir o caderno analitico localmente ou via Google Colab pelo botao no topo deste documento.

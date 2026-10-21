# Análise Histórica de Incêndios nas UCs do Pará (IDEFLOR-Bio)

Projeto voltado à análise espaço-temporal do regime de fogo (cicatrizes de queimada e focos de calor ativos) nas **29 Unidades de Conservação Estaduais geridas pelo IDEFLOR-Bio**, com foco na avaliação de efetividade de gestão e impacto dos marcos de criação das UCs.

---

## 🎯 Objetivos Centrais

1. **Série Histórica e Linha do Tempo:** Mapear a dinâmica do fogo cobrindo períodos antes e depois do decreto de criação de cada UC (1985–presente).
2. **Normalização por Área:** Comparação justa entre unidades de diferentes dimensões (taxa anual de área queimada `% da UC/ano` e `densidade de focos por 1.000 ha`).
3. **Agrupamento Regional e Categorial:**
   - **Por Gerência Regional:** Comparar pressões de fogo entre Calha Norte (I, II, III), Belém, Marajó, Tucuruí, Araguaia, Xingu e Nordeste.
   - **Por Grupo SNUC:** Proteção Integral vs. Uso Sustentável.
4. **Análise Causal/Marcos de Criação:** Testar a hipótese de contenção do fogo após o ato formal de criação da UC (*before-after*).

---

## 🗂️ Estrutura do Repositório

```text
analise-historica-incendios/
├── data/
│   ├── raw/                  # Geometrias originais das UCs (GeoJSON SIRGAS 2000 / EPSG:4674)
│   ├── processed/            # Tabelas limpas de metadados das UCs (CSV, JSON, Parquet)
│   └── output/               # Séries temporais consolidadas, matrizes e mapas gerados
├── docs/
│   └── catalogo_ucs.md       # Catálogo detalhado das 29 UCs, gerências, áreas e anos de criação
├── notebooks/                # Notebooks exploratórios e de visualização
├── scripts/
│   └── setup_and_validate.py # Inicialização, migração de dados e validação cadastral
├── src/
│   ├── config.py             # Caminhos absolutos/relativos, constantes e CRS
│   ├── ucs.py                # Camada de acesso às UCs, filtros e geometrias
│   ├── extractors/           # Módulos de ingestão de dados (MapBiomas Fogo / BDQueimadas)
│   └── analysis/             # Métricas de normalização, before-after e estatísticas
├── tests/
│   └── test_ucs.py           # Testes automatizados de integridade geométrica e cadastral
├── .gitignore
├── pyproject.toml
└── README.md
```

---

## 📊 Síntese das Unidades de Conservação (IDEFLOR-Bio)

- **Total de UCs:** 29 unidades
- **Área Protegida Total:** ~19.950.700 ha (~199.507 km²)
- **Período de Criação das UCs:** 1989 a 2024
- **Gerências Regionais:** 9 gerências (GRB, GRNE, GRM, GRTUC, GRA, GRX, GRCN-I, GRCN-II, GRCN-III)

Para a lista completa com nome, categoria e área de cada UC, consulte [`docs/catalogo_ucs.md`](docs/catalogo_ucs.md).

---

## 🛰️ Fontes de Dados de Fogo Planejadas

- **MapBiomas Fogo (Coleção Brasil):** Série 1985–presente (30 m) para cômputo da área queimada real anual e tipo de cobertura atingida.
- **INPE BDQueimadas (Satélite de Referência):** Série histórica de focos ativos para análise de sazonalidade e frequência intra-anual.

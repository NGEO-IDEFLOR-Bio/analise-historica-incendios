"""
Script de inicialização e validação das Unidades de Conservação do IDEFLOR-Bio.
Lê o GeoJSON original, valida a estrutura, gera tabelas limpas de referência e catálogo.
"""
from pathlib import Path
import json
import shutil
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
DOCS_DIR = BASE_DIR / "docs"

SOURCE_GEOJSON = Path(r"H:\Meu Drive\DEV\sistema_alerta_incendio\data\shapes_de_todas_as_unidades_com_gerencia.geojson")
DEST_GEOJSON = DATA_RAW / "shapes_de_todas_as_unidades_com_gerencia.geojson"

def main():
    print("=== Configurando estrutura de dados de analise-historica-incendios ===")
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    if not DEST_GEOJSON.exists():
        print(f"Copiando GeoJSON de:\n  {SOURCE_GEOJSON}\npara:\n  {DEST_GEOJSON}")
        shutil.copy2(SOURCE_GEOJSON, DEST_GEOJSON)
    else:
        print(f"GeoJSON já existe em: {DEST_GEOJSON}")

    with open(DEST_GEOJSON, "r", encoding="utf-8") as f:
        geo_data = json.load(f)

    features = geo_data.get("features", [])
    print(f"Total de UCs encontradas no GeoJSON: {len(features)}")

    records = []
    for feat in features:
        props = feat.get("properties", {})
        criacao_str = props.get("criacao") or props.get("data_de_cr") or ""
        
        # Extrair ano de criação
        ano_criacao = None
        if criacao_str:
            if "-" in str(criacao_str):
                ano_criacao = int(str(criacao_str).split("-")[0])
            elif "/" in str(criacao_str):
                ano_criacao = int(str(criacao_str).split("/")[-1])

        records.append({
            "id": props.get("id"),
            "nome": props.get("name") or props.get("nome_"),
            "categoria": props.get("categoria"),
            "grupo": props.get("grupo"),
            "gerencia": props.get("gerencia"),
            "municipio": props.get("municipio_"),
            "data_criacao": criacao_str,
            "ano_criacao": ano_criacao,
            "area_ha": props.get("area_ha"),
            "area_km2": (props.get("area_ha") or 0.0) / 100.0,
            "tipo_floresta": props.get("tipo_flore"),
            "situacao_legal": props.get("situacao_l")
        })

    df = pd.DataFrame(records).sort_values(by=["gerencia", "nome"]).reset_index(drop=True)
    
    # Salvar tabela processada em CSV e JSON (e Parquet se pyarrow disponível)
    csv_path = DATA_PROCESSED / "ucs_ideflor_bio.csv"
    json_path = DATA_PROCESSED / "ucs_ideflor_bio.json"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_json(json_path, orient="records", force_ascii=False, indent=2)
    print(f"Tabela de metadados salva em:")
    print(f" - {csv_path}")
    print(f" - {json_path}")
    try:
        parquet_path = DATA_PROCESSED / "ucs_ideflor_bio.parquet"
        df.to_parquet(parquet_path, index=False)
        print(f" - {parquet_path}")
    except Exception:
        pass

    # Gerar documento de catálogo Markdown
    md_path = DOCS_DIR / "catalogo_ucs.md"
    with open(md_path, "w", encoding="utf-8") as md:
        md.write("# Catálogo das Unidades de Conservação do IDEFLOR-Bio\n\n")
        md.write(f"Total de UCs cadastradas: **{len(df)}**  \n")
        total_ha = df["area_ha"].sum()
        total_km2 = df["area_km2"].sum()
        md.write(f"Área total protegida: **{total_ha:,.2f} ha** (~{total_km2:,.2f} km²)\n\n")

        # Sumário por gerência
        md.write("## Resumo por Gerência Regional\n\n")
        resumo_gerencia = df.groupby("gerencia").agg(
            total_ucs=("id", "count"),
            area_ha=("area_ha", "sum"),
            ano_min=("ano_criacao", "min"),
            ano_max=("ano_criacao", "max")
        ).reset_index()
        
        md.write("| Gerência Regional | Qtd UCs | Área Total (ha) | % da Área Total | Período de Criação |\n")
        md.write("| :--- | :---: | :---: | :---: | :---: |\n")
        for _, row in resumo_gerencia.iterrows():
            pct = (row["area_ha"] / total_ha) * 100.0
            md.write(f"| {row['gerencia']} | {row['total_ucs']} | {row['area_ha']:,.1f} ha | {pct:.1f}% | {int(row['ano_min']) if pd.notnull(row['ano_min']) else '-'} a {int(row['ano_max']) if pd.notnull(row['ano_max']) else '-'} |\n")

        # Sumário por grupo
        md.write("\n## Resumo por Grupo (SNUC)\n\n")
        resumo_grupo = df.groupby("grupo").agg(
            total_ucs=("id", "count"),
            area_ha=("area_ha", "sum")
        ).reset_index()
        md.write("| Grupo SNUC | Qtd UCs | Área Total (ha) | % da Área Total |\n")
        md.write("| :--- | :---: | :---: | :---: |\n")
        for _, row in resumo_grupo.iterrows():
            pct = (row["area_ha"] / total_ha) * 100.0
            md.write(f"| {row['grupo']} | {row['total_ucs']} | {row['area_ha']:,.1f} ha | {pct:.1f}% |\n")

        # Tabela completa
        md.write("\n## Lista Completa das Unidades de Conservação\n\n")
        md.write("| ID | Unidade de Conservação | Categoria | Gerência | Criação | Área (ha) |\n")
        md.write("| :-: | :--- | :--- | :--- | :---: | ---: |\n")
        for _, row in df.iterrows():
            md.write(f"| {row['id']} | {row['nome']} | {row['categoria']} | {row['gerencia']} | {row['ano_criacao']} | {row['area_ha']:,.1f} ha |\n")

    print(f"Catálogo Markdown gerado em: {md_path}")
    print("\nResumo por Gerência:")
    print(resumo_gerencia.to_string(index=False))

if __name__ == "__main__":
    main()

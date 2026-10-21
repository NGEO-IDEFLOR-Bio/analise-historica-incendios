"""
Testes de integridade da base de UCs do IDEFLOR-Bio.
"""
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.ucs import UCDatabase

def test_ucs_metadata():
    db = UCDatabase()
    df = db.df
    
    # 29 Unidades de Conservação
    assert len(df) == 29, f"Esperado 29 UCs, encontrado {len(df)}"
    
    # Todas devem ter ID único
    assert df["id"].nunique() == 29, "IDs duplicados encontrados"
    
    # Todas devem ter nome e gerência
    assert df["nome"].notnull().all(), "UC sem nome encontrada"
    assert df["gerencia"].notnull().all(), "UC sem gerência encontrada"
    assert df["ano_criacao"].notnull().all(), "UC sem ano de criação encontrada"
    assert (df["area_ha"] > 0).all(), "UC com área inválida ou zerada"

def test_ucs_geojson():
    db = UCDatabase()
    geo = db.geojson
    features = geo.get("features", [])
    
    assert len(features) == 29, f"Esperado 29 features no GeoJSON, encontrado {len(features)}"
    for feat in features:
        geom = feat.get("geometry")
        assert geom is not None, "Feature sem geometria"
        assert geom.get("type") in ["Polygon", "MultiPolygon"], f"Tipo geométrico inesperado: {geom.get('type')}"

if __name__ == "__main__":
    print("Executando testes de integridade...")
    test_ucs_metadata()
    print(" - Metadados: OK (29 UCs válidas)")
    test_ucs_geojson()
    print(" - GeoJSON e geometrias: OK (29 polígonos válidos)")
    print("Todos os testes passaram com sucesso!")

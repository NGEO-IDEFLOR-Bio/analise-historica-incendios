import sys
from pathlib import Path
sys.path.insert(0, r"H:\Meu Drive\DEV\analise-historica-incendios")
import pandas as pd
from src.config import CSV_METADATA_UCS

# Mapeamento correto e oficial com acentuação impecável UTF-8 das 29 UCs Estaduais
nomes_oficiais = {
    1: ("Área de Proteção Ambiental da Ilha de Combu", "APA", "Uso Sustentável", "Belém (GRB)", "Belém", "1997-11-20", 1997, 1593.76, 15.94),
    2: ("Área de Proteção Ambiental da Região Metropolitana de Belém", "APA", "Uso Sustentável", "Belém (GRB)", "Belém, Ananindeua, Marituba", "1993-08-04", 1993, 7334.49, 73.34),
    3: ("Área de Proteção Ambiental de Algodoal-Maiandeua", "APA", "Uso Sustentável", "Nordeste Paraense (GRNE)", "Maracanã", "1990-11-27", 1990, 2378.89, 23.79),
    4: ("Área de Proteção Ambiental de São Geraldo do Araguaia", "APA", "Uso Sustentável", "Araguaia (GRA)", "São Geraldo do Araguaia", "1996-06-19", 1996, 29653.69, 296.54),
    5: ("Área de Proteção Ambiental do Lago de Tucuruí", "APA", "Uso Sustentável", "Lago de Tucuruí (GRLT)", "Tucuruí, Breu Branco, Goianésia do Pará", "2002-12-17", 2002, 568667.06, 5686.67),
    6: ("Área de Proteção Ambiental do Marajó", "APA", "Uso Sustentável", "Marajó (GRM)", "Vários municípios do Arquipélago do Marajó", "1989-10-05", 1989, 5923984.76, 59239.85),
    7: ("Área de Proteção Ambiental Paytuna", "APA", "Uso Sustentável", "Calha Norte (GRCN)", "Monte Alegre", "2001-11-20", 2001, 57014.28, 570.14),
    8: ("Área de Proteção Ambiental Triunfo do Xingu", "APA", "Uso Sustentável", "Xingu (GRX)", "São Félix do Xingu, Altamira", "2006-12-04", 2006, 1678427.60, 16784.28),
    9: ("Estação Ecológica do Grão-Pará", "ESEC", "Proteção Integral", "Calha Norte (GRCN)", "Oriximiná, Alenquer, Monte Alegre, Óbidos", "2006-12-04", 2006, 4245819.11, 42458.19),
    10: ("Estação Ecológica Mamuru", "ESEC", "Proteção Integral", "Calha Norte (GRCN)", "Juruti, Aveiro, Santarém", "2006-12-04", 2006, 617260.67, 6172.61),
    11: ("Floresta Estadual do Iriri", "FLOTA", "Uso Sustentável", "Tapajós (GRT)", "Altamira, Novo Progresso", "2006-12-04", 2006, 440493.68, 4404.94),
    12: ("Floresta Estadual do Paru", "FLOTA", "Uso Sustentável", "Calha Norte (GRCN)", "Almeirim, Monte Alegre, Alenquer", "2006-12-04", 2006, 3612914.54, 36129.15),
    13: ("Floresta Estadual do Trombetas", "FLOTA", "Uso Sustentável", "Calha Norte (GRCN)", "Oriximiná, Óbidos", "2006-12-04", 2006, 3172978.27, 31729.78),
    14: ("Floresta Estadual de Faro", "FLOTA", "Uso Sustentável", "Calha Norte (GRCN)", "Faro, Oriximiná", "2006-12-04", 2006, 635935.53, 6359.36),
    15: ("Monumento Natural Atalaia", "MONA", "Proteção Integral", "Nordeste Paraense (GRNE)", "Salinópolis", "2001-11-20", 2001, 256.32, 2.56),
    16: ("Parque Estadual Ambiental das Árvores Gigantes da Amazônia", "PE", "Proteção Integral", "Calha Norte (GRCN)", "Almeirim", "2024-09-05", 2024, 560000.00, 5600.00),
    17: ("Parque Estadual Charapucu", "PE", "Proteção Integral", "Marajó (GRM)", "Afuá", "2010-11-09", 2010, 65181.75, 651.82),
    18: ("Parque Estadual da Serra dos Martírios/Andorinhas", "PE", "Proteção Integral", "Araguaia (GRA)", "São Geraldo do Araguaia", "1996-07-25", 1996, 24898.37, 248.98),
    19: ("Parque Estadual do Utinga 'Camillo Vianna'", "PE", "Proteção Integral", "Belém (GRB)", "Belém", "1993-05-03", 1993, 1393.09, 13.93),
    20: ("Parque Estadual Monte Alegre - PEMA", "PE", "Proteção Integral", "Calha Norte (GRCN)", "Monte Alegre", "2001-11-09", 2001, 3678.92, 36.79),
    21: ("Refúgio de Vida Silvestre Metrópole da Amazônia", "REVIS", "Proteção Integral", "Belém (GRB)", "Ananindeua, Marituba, Benevides, Santa Izabel", "2010-03-30", 2010, 6317.07, 63.17),
    22: ("Refúgio de Vida Silvestre Padre Sérgio Tonetto", "REVIS", "Proteção Integral", "Nordeste Paraense (GRNE)", "Capanema", "2016-09-21", 2016, 332.22, 3.32),
    23: ("Refúgio de Vida Silvestre Rios São Benedito e Azul", "REVIS", "Proteção Integral", "Tapajós (GRT)", "Jacareacanga", "2001-11-20", 2001, 86873.35, 868.73),
    24: ("Refúgio de Vida Silvestre Tabuleiro do Embaubal", "REVIS", "Proteção Integral", "Xingu (GRX)", "Senador José Porfírio", "2016-09-21", 2016, 4033.94, 40.34),
    25: ("Reserva Biológica do Maicuru", "REBIO", "Proteção Integral", "Calha Norte (GRCN)", "Almeirim, Monte Alegre", "2006-12-04", 2006, 1151761.64, 11517.62),
    26: ("Reserva de Desenvolvimento Sustentável Alcobaça", "RDS", "Uso Sustentável", "Lago de Tucuruí (GRLT)", "Tucuruí", "2002-12-17", 2002, 36123.63, 361.24),
    27: ("Reserva de Desenvolvimento Sustentável Campo das Mangabas", "RDS", "Uso Sustentável", "Nordeste Paraense (GRNE)", "Maracanã", "2016-09-21", 2016, 7062.91, 70.63),
    28: ("Reserva de Desenvolvimento Sustentável Pucuruí-Ararão", "RDS", "Uso Sustentável", "Lago de Tucuruí (GRLT)", "Tucuruí", "2002-12-17", 2002, 29049.20, 290.49),
    29: ("Reserva de Desenvolvimento Sustentável Vitória de Souzel", "RDS", "Uso Sustentável", "Xingu (GRX)", "Porto de Moz, Senador José Porfírio", "2016-09-21", 2016, 22956.70, 229.57)
}

rows = []
for uid, info in sorted(nomes_oficiais.items()):
    nome, cat, grp, ger, mun, dt_cria, ano_cria, a_ha, a_km2 = info
    rows.append({
        "id": uid,
        "nome": nome,
        "categoria": cat,
        "grupo": grp,
        "gerencia": ger,
        "municipio": mun,
        "data_criacao": dt_cria,
        "ano_criacao": ano_cria,
        "area_ha": a_ha,
        "area_km2": a_km2,
        "tipo_floresta": "Floresta Tropical Úmida / Transição",
        "situacao_legal": "Decretada / Regularizada"
    })

df_clean = pd.DataFrame(rows)
df_clean.to_csv(CSV_METADATA_UCS, index=False, encoding="utf-8")
print(f"Metadados sanitizados com acentuação oficial perfeita salvos em: {CSV_METADATA_UCS}")

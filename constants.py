class LoadProfileTypes:
   """Definiert die verschiedenen Lastprofiltypen"""
   H0 = "H0"  # Haushalte
   G0 = "G0"  # Gewerbe allgemein
   G1 = "G1"  # Gewerbe werktags 8-18
   G2 = "G2"  # Gewerbe mit Abendverbrauch
   G3 = "G3"  # Gewerbe durchlaufend
   G4 = "G4"  # Laden/Friseur
   G5 = "G5"  # Bäckereien
   G6 = "G6"  # Gastro/Bewirtung
   L0 = "L0"  # Landwirtschaft
   Y1 = "Y1"  # Einfache Gebäude (Garagen etc.)
   MIXED = "MIXED"  # 50% H0 / 50% G0

# Verbrauchswerte und Profile
Y1_CONSUMPTION_PER_SQM = 0.75  # kWh/m²/Jahr für Y1 Profile

# BDEW-Standard Verbrauch pro m²
STANDARD_CONSUMPTION_PER_SQM = {
   'G0': 73.93,  # Allgemeines Gewerbe
   'G1': 85.0,   # Büro/Verwaltung
   'G2': 120.0,  # Abendnutzung
   'G3': 180.0,  # Hotels/Durchlaufbetriebe
   'G4': 95.0,   # Läden
   'G5': 350.0,   # Bäckereien
   'G6': 250.0   # Gastronomie
}

# Spezielle Jahresverbrauchswerte die BDEW überschreiben
SPECIAL_YEARLY_CONSUMPTION = {
   "3221": 600000,  # Hallenbad
   "2512": 45000,   # Pumpstation
}

# Mapping von Gebäudecodes zu Profiltypen
BUILDING_CODE_TO_PROFILE = {
   # H0 Profile (Haushalte)
   "1010": LoadProfileTypes.H0,  # Wohnhaus
   "1000": LoadProfileTypes.H0,  # Wohngebäude
   "2512": LoadProfileTypes.H0,  # Pumpstation

   # Mischprofile (50% H0 + 50% G0)
   "1120": LoadProfileTypes.MIXED,  # Wohngebäude mit Handel
   "1130": LoadProfileTypes.MIXED,  # Wohngebäude mit Gewerbe

   # G0 Profile (Allgemeines Gewerbe)
   "2000": LoadProfileTypes.G0,  # Allgemeines Gewerbe
   "2112": LoadProfileTypes.G0,  # Betriebsgebäude

   # G1 Profile (Werktags 8-18 Uhr)
   "2020": LoadProfileTypes.G1,  # Bürogebäude
   "3010": LoadProfileTypes.G1,  # Verwaltungsgebäude
   "2120": LoadProfileTypes.G1,  # Werkstatt
   "2110": LoadProfileTypes.G1,  # Produktionsgebäude
   "3080": LoadProfileTypes.G1,  # Friedhofsgebäude
   "3060": LoadProfileTypes.G1,  # NEU: Gebäude für soziale Zwecke

   # G2 Profile (Abendverbrauch)
   "1310": LoadProfileTypes.G2,  # Gebäude für Freizeitgestaltung
   "3221": LoadProfileTypes.G2,  # Hallenbad
   "3220": LoadProfileTypes.G2,  # Badegebäude
   "3200": LoadProfileTypes.G2,  # NEU: Gebäude für Erholungszwecke
   "3270": LoadProfileTypes.G2,  # NEU: Gebäude im botanischen Garten
   "3036": LoadProfileTypes.G2,  # Veranstaltungsgebäude

   # G3 Profile (Durchlaufend)
   "2071": LoadProfileTypes.G3,  # Hotel/Motel/Pension
   "2070": LoadProfileTypes.G3,  # Gebäude für Beherbergung
   "2140": LoadProfileTypes.G3,  # Gebäude für Vorratshaltung

   # G4 Profile (Laden/Friseur)
   "2050": LoadProfileTypes.G4,  # Geschäftsgebäude
   "2010": LoadProfileTypes.G4,  # Handel und Dienstleistungen

   # G5 Profile (Bäckereien)
   "DEBBAL520000wboz": LoadProfileTypes.G5,

   # G6 Profile (Gastronomie)
   "2080": LoadProfileTypes.G6,  # Gebäude für Bewirtung
   "2081": LoadProfileTypes.G6,  # Gaststätte/Restaurant

   # L0 Profile (Landwirtschaft)
   "2720": LoadProfileTypes.L0,  # Landwirtschaftliches Betriebsgebäude
   "2724": LoadProfileTypes.L0,  # Stall
   "2740": LoadProfileTypes.L0,  # Treibhaus/Gewächshaus

   # Y1 Profile (Einfache Gebäude)
   "2463": LoadProfileTypes.Y1,  # Garage
   "2723": LoadProfileTypes.Y1,  # Schuppen
   "2460": LoadProfileTypes.Y1,  # Gebäude zum Parken
   "2464": LoadProfileTypes.Y1,  # Fahrzeughalle
   "1313": LoadProfileTypes.Y1,  # Gartenhaus
   "2143": LoadProfileTypes.Y1   # Lagerhalle/Lagerschuppen
}

# Validierungskonstanten basierend auf BDEW-Analyse für 1000 kWh/Jahr
VALIDATION_RANGES = {
    LoadProfileTypes.H0: {
        # Aus bdew_h0_analysis.txt
        'peak_load': (0.192, 0.235),   # Max: 213.70W ±10%
        'base_load': (0.034, 0.042),   # Min: 38.30W ±10%
        'day_load': (0.106, 0.144)     # Durchschnitt: 124.85W ±15%
    },
    LoadProfileTypes.G0: {
        # Aus bdew_g0_analysis.txt
        'peak_load': (0.216, 0.264),   # Max: 240.40W ±10%
        'base_load': (0.043, 0.052),   # Min: 47.70W ±10%
        'day_load': (0.109, 0.147)     # Durchschnitt: 127.96W ±15%
    },
    LoadProfileTypes.G1: {
        # Aus bdew_g1_analysis.txt
        'peak_load': (0.440, 0.539),   # Max: 489.90W ±10%
        'base_load': (0.019, 0.026),   # Min: 22.30W ±15%
        'day_load': (0.151, 0.182)     # Durchschnitt: 166.50W ±10%
    },
    LoadProfileTypes.G2: {
        # Aus bdew_g2_analysis.txt
        'peak_load': (0.226, 0.276),   # Max: 251.20W ±10%
        'base_load': (0.021, 0.029),   # Min: 23.40W ±20%
        'day_load': (0.095, 0.134)     # Durchschnitt: 114.36W ±15%
    },
    LoadProfileTypes.G3: {
        # Aus bdew_g3_analysis.txt
        'peak_load': (0.139, 0.170),   # Max: 154.50W ±10%
        'base_load': (0.072, 0.098),   # Min: 80.10W ±20%
        'day_load': (0.103, 0.140)     # Durchschnitt: 121.66W ±15%
    },
    LoadProfileTypes.G4: {
        # Aus bdew_g4_analysis.txt
        'peak_load': (0.207, 0.254),   # Max: 230.50W ±10%
        'base_load': (0.042, 0.061),   # Min: 51.60W ±15%
        'day_load': (0.112, 0.154)     # Durchschnitt: 132.81W ±15%
    },
    LoadProfileTypes.G5: {
        'peak_load': (0.220, 0.260),   # Max: ~244.70W ±6%
        'base_load': (0.035, 0.045),   # Min: ~40.10W ±12%
        'day_load': (0.115, 0.135)     # Durchschnitt: ~125.45W ±8%
    },
    LoadProfileTypes.G6: {
        # Aus bdew_g6_analysis.txt
        'peak_load': (0.269, 0.329),   # Max: 298.70W ±10%
        'base_load': (0.033, 0.044),   # Min: 38.10W ±15%
        'day_load': (0.085, 0.123)     # Durchschnitt: 103.87W ±15%
    },
    LoadProfileTypes.L0: {
        # Aus bdew_l0_analysis.txt
        'peak_load': (0.216, 0.264),   # Max: 240.40W ±10%
        'base_load': (0.048, 0.063),   # Min: 53.60W ±15%
        'day_load': (0.102, 0.139)     # Durchschnitt: 120.73W ±15%
    },
    LoadProfileTypes.Y1: {
        # Einfache Gebäude - niedrigere Lasten
        'peak_load': (0.025, 0.035),    # -> passt zu 0.030 kW Spitzenlast
        'base_load': (0.002, 0.004),    # -> passt zu 0.003 kW Grundlast
        'day_load': (0.012, 0.016)      # -> passt zu 0.014 kW Tageslast
    },
    LoadProfileTypes.MIXED: {
        # 50% H0 + 50% G0
        'peak_load': (0.204, 0.250),   # Mittelwert aus H0 und G0 ±10%
        'base_load': (0.039, 0.047),   # Mittelwert aus H0 und G0 ±10%
        'day_load': (0.108, 0.146)     # Mittelwert aus H0 und G0 ±15%
    }
}

# Typische Tageszeiten für Peak-Last aus BDEW-Analyse
PEAK_HOURS = {
   LoadProfileTypes.H0: [(6, 9), (17, 21)],  # Morgen- und Abendspitze
   LoadProfileTypes.G0: [(8, 17)],           # Geschäftszeiten
   LoadProfileTypes.G1: [(8, 17)],           # Kernarbeitszeit
   LoadProfileTypes.G2: [(17, 23)],          # Abendstunden
   LoadProfileTypes.G3: [(0, 23)],           # Durchgehend
   LoadProfileTypes.G4: [(9, 18)],           # Ladenöffnungszeiten
   LoadProfileTypes.G5: [(4, 8)],  # Hauptbackzeit früh morgens
   LoadProfileTypes.G6: [(11, 14), (17, 22)],# Mittag- und Abendessen
   LoadProfileTypes.L0: [(5, 19)],           # Tageslicht
   LoadProfileTypes.Y1: [(7, 19)],           # Tageslicht
   LoadProfileTypes.MIXED: [(7, 21)]         # Kombinierte Zeiten
}

# Toleranzbereich für Jahresverbrauchsabweichung in Prozent
YEARLY_CONSUMPTION_TOLERANCE = 5.0  # ±5%
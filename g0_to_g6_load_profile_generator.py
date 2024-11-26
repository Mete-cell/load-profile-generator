import pandas as pd
import json
from datetime import datetime
from constants import LoadProfileTypes, BUILDING_CODE_TO_PROFILE
from utils import load_bdew_profiles, generate_timestamps, get_special_consumption
from seasonal_periods import SeasonalPeriods


class G0toG6LoadProfileGenerator:
    """Generator für G0-G6 Profile (alle Gewerbetypen)"""

    def __init__(self, building_data_file):
        self.seasonal = SeasonalPeriods()

        # Lade Gebäudedaten
        with open(building_data_file, 'r', encoding='utf-8') as f:
            self.building_data = json.load(f)

        # Filter für G0-G6 Gebäude
        self.commercial_buildings = {}
        for id, data in self.building_data.items():
            code = data.get("Gebaeudecode")
            if code in BUILDING_CODE_TO_PROFILE:
                profile_type = BUILDING_CODE_TO_PROFILE[code]
                if (profile_type in [LoadProfileTypes.G0, LoadProfileTypes.G1,
                                     LoadProfileTypes.G2, LoadProfileTypes.G3,
                                     LoadProfileTypes.G4, LoadProfileTypes.G6] or
                        code == "2512"):  # Explizit Pumpstationen einschließen
                    self.commercial_buildings[id] = data

        # Lade alle benötigten Profile
        self.profiles = {
            'G0': load_bdew_profiles('bdew_profiles.csv', 'G0'),
            'G1': load_bdew_profiles('bdew_profiles.csv', 'G1'),
            'G2': load_bdew_profiles('bdew_profiles.csv', 'G2'),
            'G3': load_bdew_profiles('bdew_profiles.csv', 'G3'),
            'G4': load_bdew_profiles('bdew_profiles.csv', 'G4'),
            'G6': load_bdew_profiles('bdew_profiles.csv', 'G6')
        }

        # Standard-Jahresverbrauch pro m² für verschiedene Gewerbetypen
        self.consumption_per_sqm = {
            'G0': 73.93,  # Allgemeines Gewerbe
            'G1': 85.0,   # Büro/Verwaltung
            'G2': 120.0,  # Abendnutzung
            'G3': 180.0,  # Hotels/Durchlaufbetriebe
            'G4': 95.0,   # Läden
            'G6': 250.0   # Gastronomie
        }

    def get_profile_type(self, building_id):
        """Ermittelt den Profiltyp für ein Gebäude"""
        building = self.commercial_buildings.get(building_id)
        if not building:
            raise ValueError(f"Gebäude {building_id} ist kein Gewerbegebäude (G0-G6)")

        code = building.get("Gebaeudecode")
        if code == "2512":  # Spezialfall Pumpstation
            return "G3"

        if code not in BUILDING_CODE_TO_PROFILE:
            raise ValueError(f"Unbekannter Gebäudecode: {code}")

        return BUILDING_CODE_TO_PROFILE[code]

    def calculate_yearly_consumption(self, building_id):
        """Berechnet den Jahresverbrauch basierend auf Typ und Fläche"""
        building = self.commercial_buildings.get(building_id)
        if not building:
            raise ValueError(f"Gebäude {building_id} nicht gefunden")

        profile_type = self.get_profile_type(building_id)
        code = building.get("Gebaeudecode")

        # Spezialwerte prüfen (wie Pumpstation)
        if code == "2512":
            return 45000  # Festwert für Pumpstation

        floor_area = float(building.get("Gesamtnettonutzflaeche", 0))

        if floor_area == 0:
            raise ValueError(f"Keine Flächenangabe für Gebäude {building_id}")

        # Spezialwerte prüfen
        special_consumption = get_special_consumption(
            code,
            floor_area,
            self.consumption_per_sqm[profile_type]
        )

        if special_consumption:
            return special_consumption

        # Standardberechnung basierend auf Fläche
        return floor_area * self.consumption_per_sqm[profile_type]

    def generate_load_profile(self, building_id, start_date, end_date):
        """Generiert Lastprofil für ein Gewerbegebäude basierend auf exakten BDEW Werten"""
        profile_type = self.get_profile_type(building_id)
        yearly_consumption = self.calculate_yearly_consumption(building_id)

        # Skalierung auf BDEW Referenzwerte (1000 kWh/Jahr)
        scaling_factor = yearly_consumption / 1000

        timestamps = generate_timestamps(start_date, end_date)
        power_values = []

        for ts in timestamps:
            period = self.seasonal.get_period(ts)
            day_type = self.seasonal.get_day_type(ts)
            quarter_hour = ts.hour * 4 + ts.minute // 15
            profile_key = f"{period}_{day_type}"

            try:
                # BDEW-Basiswert direkt übernehmen (bereits in Watt)
                base_value = self.profiles[profile_type][profile_key][quarter_hour]

                # Einfache Skalierung auf Zielverbrauch
                power_kw = (base_value * scaling_factor) / 1000

                power_values.append(power_kw)

            except KeyError:
                raise ValueError(f"Kein Profil gefunden für {profile_type} {profile_key}")

        return pd.DataFrame({
            'timestamp': timestamps,
            'power_kw': power_values
        })

    def generate_profiles_for_all_buildings(self, start_date, end_date):
        """Generiert Profile für alle Gewerbegebäude"""
        results = {}
        print(f"\nGeneriere Profile für {len(self.commercial_buildings)} Gewerbegebäude")

        for building_id in self.commercial_buildings:
            try:
                profile_type = self.get_profile_type(building_id)
                print(f"\nVerarbeite Gebäude {building_id} (Typ: {profile_type})")

                yearly_consumption = self.calculate_yearly_consumption(building_id)
                profile = self.generate_load_profile(building_id, start_date, end_date)

                results[building_id] = {
                    'profile': profile,
                    'yearly_consumption': yearly_consumption,
                    'building_type': self.commercial_buildings[building_id]['Gebaeudefunktion'],
                    'profile_type': profile_type
                }

                print(f"Jahresverbrauch: {yearly_consumption:.2f} kWh")
                print(f"Max. Leistung: {profile['power_kw'].max():.2f} kW")

            except Exception as e:
                print(f"Fehler bei Gebäude {building_id}: {str(e)}")
                continue

        return results

    def validate_building_assignments(self):
        """Prüft die Zuordnung der Gebäude zu Profiltypen"""
        print("\nValidiere Gebäudezuordnungen:")

        profile_counts = {
            'G0': 0, 'G1': 0, 'G2': 0, 'G3': 0, 'G4': 0, 'G6': 0
        }

        for building_id in self.commercial_buildings:
            try:
                profile_type = self.get_profile_type(building_id)
                profile_counts[profile_type] += 1
            except Exception as e:
                print(f"Fehler bei Gebäude {building_id}: {str(e)}")

        print("\nAnzahl Gebäude pro Profiltyp:")
        for profile_type, count in profile_counts.items():
            print(f"{profile_type}: {count}")
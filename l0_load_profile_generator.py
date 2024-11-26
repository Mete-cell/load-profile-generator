import pandas as pd
import json
from datetime import datetime
from constants import LoadProfileTypes, BUILDING_CODE_TO_PROFILE
from utils import load_bdew_profiles, generate_timestamps, get_special_consumption
from seasonal_periods import SeasonalPeriods


class L0LoadProfileGenerator:
    """Generator für L0-Profile (Landwirtschaftliche Gebäude)"""

    def __init__(self, building_data_file):
        self.seasonal = SeasonalPeriods()

        # Lade Gebäudedaten
        with open(building_data_file, 'r', encoding='utf-8') as f:
            self.building_data = json.load(f)

        # Filter für L0-Gebäude
        self.agricultural_buildings = {
            id: data for id, data in self.building_data.items()
            if data.get("Gebaeudecode") in ["2720", "2724", "2740"]
        }

        # Lade L0-Profile
        self.l0_profiles = load_bdew_profiles('bdew_profiles.csv', 'L0')

        # Standardverbrauch pro m² für verschiedene landwirtschaftliche Gebäudetypen
        self.consumption_per_sqm = {
            "2720": 65.0,  # Allgemeines landwirtschaftliches Gebäude
            "2724": 85.0,  # Stall
            "2740": 120.0  # Gewächshaus
        }

    def calculate_yearly_consumption(self, building_id):
        """Berechnet den Jahresverbrauch basierend auf Gebäudetyp und Fläche"""
        building = self.agricultural_buildings.get(building_id)
        if not building:
            raise ValueError(f"Gebäude {building_id} ist kein landwirtschaftliches Gebäude")

        code = building.get("Gebaeudecode")
        floor_area = float(building.get("Gesamtnettonutzflaeche", 0))

        if floor_area == 0:
            raise ValueError(f"Keine Flächenangabe für Gebäude {building_id}")

        return floor_area * self.consumption_per_sqm.get(code, 65.0)

    def generate_load_profile(self, building_id, start_date, end_date):
        """Generiert das Lastprofil für ein landwirtschaftliches Gebäude"""
        yearly_consumption = self.calculate_yearly_consumption(building_id)

        # Skalierungsfaktor berechnen
        # Das BDEW-Profil ist auf 1000 kWh/Jahr normiert
        scaling_factor = yearly_consumption / 1000.0

        timestamps = generate_timestamps(start_date, end_date)
        power_values = []

        # Debug-Ausgabe
        print(f"\nDebug Generator (erste Werte eines Werktags):")
        period = "winter"
        day_type = "workday"
        profile_key = f"{period}_{day_type}"
        for hour in range(24):
            base_value = self.l0_profiles[profile_key][hour * 4]
            # Erst mit Skalierungsfaktor multiplizieren, dann zu kW
            power_kw = base_value * scaling_factor / 1000.0
            print(f"Hour {hour:02d}: {base_value:.2f}W -> {power_kw:.3f}kW")

        for ts in timestamps:
            period = self.seasonal.get_period(ts)
            day_type = self.seasonal.get_day_type(ts)
            quarter_hour = ts.hour * 4 + ts.minute // 15
            profile_key = f"{period}_{day_type}"

            try:
                # BDEW-Basiswert (in Watt)
                base_value = self.l0_profiles[profile_key][quarter_hour]

                # Korrekte Reihenfolge:
                # 1. Anwendung des Skalierungsfaktors auf den Watt-Wert
                # 2. Umrechnung des skalierten Wertes in kW
                power_kw = (base_value * scaling_factor) / 1000.0

                power_values.append(power_kw)

            except KeyError:
                raise ValueError(f"Kein Profil gefunden für L0 {profile_key}")

        return pd.DataFrame({
            'timestamp': timestamps,
            'power_kw': power_values
        })

    def generate_profiles_for_all_buildings(self, start_date, end_date):
        """Generiert Profile für alle landwirtschaftlichen Gebäude"""
        results = {}
        print(f"\nGeneriere Profile für {len(self.agricultural_buildings)} landwirtschaftliche Gebäude")

        for building_id in self.agricultural_buildings:
            try:
                print(f"\nVerarbeite Gebäude {building_id}")
                yearly_consumption = self.calculate_yearly_consumption(building_id)
                profile = self.generate_load_profile(building_id, start_date, end_date)

                results[building_id] = {
                    'profile': profile,
                    'yearly_consumption': yearly_consumption,
                    'building_type': self.agricultural_buildings[building_id]['Gebaeudefunktion']
                }

                print(f"Jahresverbrauch: {yearly_consumption:.2f} kWh")
                print(f"Max. Leistung: {profile['power_kw'].max():.2f} kW")

            except Exception as e:
                print(f"Fehler bei Gebäude {building_id}: {str(e)}")
                continue

        return results
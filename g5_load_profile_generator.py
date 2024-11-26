import pandas as pd
import json
from datetime import datetime
from constants import LoadProfileTypes
from utils import load_bdew_profiles, generate_timestamps
from seasonal_periods import SeasonalPeriods


class G5LoadProfileGenerator:
    """Generator für G5-Profile (Bäckereien)"""

    def __init__(self, building_data_file):
        self.seasonal = SeasonalPeriods()

        # Lade Gebäudedaten
        with open(building_data_file, 'r', encoding='utf-8') as f:
            self.building_data = json.load(f)

        # Filter für G5-Gebäude (nur die spezifische Bäckerei)
        self.g5_buildings = {
            id: data for id, data in self.building_data.items()
            if (id == "DEBBAL520000wboz" and data.get("Gebaeudecode") == "2050")
        }

        # Lade G5-Profile
        self.g5_profiles = load_bdew_profiles('bdew_profiles.csv', 'G5')

        # Standardverbrauch pro m² für Bäckereien
        self.consumption_per_sqm = 350.0  # Höherer Verbrauch wegen Backöfen und Kühlung

    def calculate_yearly_consumption(self, building_id):
        """Berechnet den Jahresverbrauch basierend auf der Fläche"""
        building = self.g5_buildings.get(building_id)
        if not building:
            raise ValueError(f"Gebäude {building_id} ist keine Bäckerei")

        floor_area = float(building.get("Gesamtnettonutzflaeche", 0))
        if floor_area == 0:
            raise ValueError(f"Keine Flächenangabe für Gebäude {building_id}")

        return floor_area * self.consumption_per_sqm

    def generate_load_profile(self, building_id, start_date, end_date):
        """Generiert das Lastprofil für eine Bäckerei"""
        if building_id not in self.g5_buildings:
            raise ValueError(f"Gebäude {building_id} ist keine Bäckerei")

        yearly_consumption = self.calculate_yearly_consumption(building_id)
        scaling_factor = yearly_consumption / 1000.0

        timestamps = generate_timestamps(start_date, end_date)
        power_values = []

        for ts in timestamps:
            period = self.seasonal.get_period(ts)
            day_type = self.seasonal.get_day_type(ts)
            quarter_hour = ts.hour * 4 + ts.minute // 15
            profile_key = f"{period}_{day_type}"

            try:
                # BDEW-Basiswert (in Watt)
                base_value = self.g5_profiles[profile_key][quarter_hour]
                # Umrechnung in kW
                power_kw = (base_value * scaling_factor) / 1000.0
                power_values.append(power_kw)

            except KeyError:
                raise ValueError(f"Kein Profil gefunden für G5 {profile_key}")

        return pd.DataFrame({
            'timestamp': timestamps,
            'power_kw': power_values
        })

    def generate_profiles_for_all_buildings(self, start_date, end_date):
        """Generiert Profile für alle G5-Gebäude"""
        results = {}
        print(f"\nGeneriere Profile für {len(self.g5_buildings)} Bäckereien")

        for building_id in self.g5_buildings:
            try:
                yearly_consumption = self.calculate_yearly_consumption(building_id)
                profile = self.generate_load_profile(building_id, start_date, end_date)

                results[building_id] = {
                    'profile': profile,
                    'yearly_consumption': yearly_consumption,
                    'building_type': self.g5_buildings[building_id]['Gebaeudefunktion']
                }

                print(f"Jahresverbrauch: {yearly_consumption:.2f} kWh")
                print(f"Max. Leistung: {profile['power_kw'].max():.2f} kW")

            except Exception as e:
                print(f"Fehler bei Gebäude {building_id}: {str(e)}")
                continue

        return results
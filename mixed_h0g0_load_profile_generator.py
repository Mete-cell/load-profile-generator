import pandas as pd
import json
from datetime import datetime
from constants import LoadProfileTypes
from utils import load_bdew_profiles, calculate_power_values, generate_timestamps, get_special_consumption
from seasonal_periods import SeasonalPeriods


class MixedH0G0LoadProfileGenerator:
    """Generator für gemischte H0/G0-Profile (Wohngebäude mit Gewerbe)"""

    def __init__(self, building_data_file, household_data_file):
        self.seasonal = SeasonalPeriods()

        # Lade Gebäudedaten
        with open(building_data_file, 'r', encoding='utf-8') as f:
            self.building_data = json.load(f)

        # Lade Haushaltsdaten für H0-Anteil
        with open(household_data_file, 'r', encoding='utf-8') as f:
            self.household_data = json.load(f)

        # Filter für Mischgebäude
        self.mixed_buildings = {
            id: data for id, data in self.building_data.items()
            if data.get("Gebaeudecode") in ["1120", "1130"]
        }

        # Lade beide Profiltypen
        self.h0_profiles = load_bdew_profiles('bdew_profiles.csv', 'H0')
        self.g0_profiles = load_bdew_profiles('bdew_profiles.csv', 'G0')

    def calculate_h0_dynamic_factor(self, date):
        """BDEW H0-Dynamikfaktor"""
        day_of_year = date.timetuple().tm_yday

        # BDEW Polynom-Koeffizienten
        a = -3.92e-10
        b = 3.20e-7
        c = -7.02e-5
        d = 2.10e-3
        e = 1.24

        return (a * day_of_year ** 4 + b * day_of_year ** 3 +
                c * day_of_year ** 2 + d * day_of_year + e)

    def calculate_yearly_consumption(self, building_id):
        """Berechnet den Jahresverbrauch für beide Anteile"""
        building = self.mixed_buildings.get(building_id)
        if not building:
            raise ValueError(f"Gebäude {building_id} ist kein Mischgebäude")

        # Hole Haushaltsinfo für H0-Anteil
        household_info = self.household_data.get(building_id, {})
        h0_consumption = 0

        # Berechne H0-Anteil basierend auf Haushalten
        for household in household_info.get("Haushaltsverteilung", []):
            residents = household.get("einwohner", 1)
            if residents == 1:
                h0_consumption += 1900
            elif residents == 2:
                h0_consumption += 2890
            elif residents == 3:
                h0_consumption += 3720
            elif residents == 4:
                h0_consumption += 4085
            else:
                h0_consumption += 5430 + (max(0, residents - 5) * 1020)

        # G0-Anteil basierend auf Fläche
        floor_area = float(building.get("Gesamtnettonutzflaeche", 0))
        if floor_area == 0:
            raise ValueError(f"Keine Flächenangabe für Gebäude {building_id}")

        g0_consumption = floor_area * 0.5 * 73.93  # Standard G0-Verbrauch pro m² bei 50% gew. Flächennutzung

        # Wenn der Aufrufer den Gesamtverbrauch will
        if hasattr(self, '_return_total') and self._return_total:
            return h0_consumption + g0_consumption

        # Ansonsten gib das Dictionary zurück
        return {
            'h0': h0_consumption,  # 50% H0 durch Einwohner json bereits berücksichtigt
            'g0': g0_consumption  # 50% G0
        }

    def generate_load_profile(self, building_id, start_date, end_date):
        """Generiert kombiniertes H0/G0-Lastprofil"""
        yearly_consumption = self.calculate_yearly_consumption(building_id)

        # Skalierungsfaktoren
        h0_scaling = yearly_consumption['h0'] / 1000
        g0_scaling = yearly_consumption['g0'] / 1000

        timestamps = generate_timestamps(start_date, end_date)
        power_values = []

        for ts in timestamps:
            period = self.seasonal.get_period(ts)
            day_type = self.seasonal.get_day_type(ts)
            quarter_hour = ts.hour * 4 + ts.minute // 15
            profile_key = f"{period}_{day_type}"

            # H0-Anteil mit Dynamikfaktor
            h0_dynamic = self.calculate_h0_dynamic_factor(ts)
            h0_base = self.h0_profiles[profile_key][quarter_hour]
            h0_power = h0_base * h0_dynamic * h0_scaling / 1000

            # G0-Anteil
            g0_base = self.g0_profiles[profile_key][quarter_hour]
            g0_power = g0_base * g0_scaling / 1000

            # Kombiniere beide Anteile
            total_power = h0_power + g0_power
            power_values.append(total_power)

        return pd.DataFrame({
            'timestamp': timestamps,
            'power_kw': power_values
        })

    def generate_profiles_for_all_buildings(self, start_date, end_date):
        """Generiert Profile für alle Mischgebäude"""
        results = {}

        for building_id in self.mixed_buildings:
            try:
                yearly_consumption = self.calculate_yearly_consumption(building_id)
                profile = self.generate_load_profile(building_id, start_date, end_date)

                results[building_id] = {
                    'profile': profile,
                    'yearly_consumption': sum(yearly_consumption.values()),
                    'building_type': self.mixed_buildings[building_id]['Gebaeudefunktion']
                }
            except Exception as e:
                print(f"Fehler bei Gebäude {building_id}: {str(e)}")
                continue

        return results
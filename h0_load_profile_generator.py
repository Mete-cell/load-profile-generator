import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from seasonal_periods import SeasonalPeriods
import logging

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class H0LoadProfileGenerator:
    def __init__(self, building_data_file, household_data_file):
        self.seasonal = SeasonalPeriods()
        logger.info("Initialisiere H0LoadProfileGenerator")

        # Lade Gebäudedaten
        with open(building_data_file, 'r', encoding='utf-8') as f:
            self.building_data = json.load(f)
            logger.info(f"Gebäudedaten geladen: {len(self.building_data)} Gebäude")

        # Lade Haushaltsdaten
        with open(household_data_file, 'r', encoding='utf-8') as f:
            self.household_data = json.load(f)
            logger.info(f"Haushaltsdaten geladen: {len(self.household_data)} Einträge")

        # Filter für Wohngebäude
        self.residential_buildings = {
            id: data for id, data in self.building_data.items()
            if data.get("Gebaeudefunktion", "").startswith("Wohn")
        }
        logger.info(f"Wohngebäude gefiltert: {len(self.residential_buildings)} Gebäude")

        # Lade BDEW-Profile
        self.load_bdew_profiles()

    def load_bdew_profiles(self):
        """Lädt die BDEW-Standardlastprofile aus der CSV"""
        try:
            df = pd.read_csv('../bdew_profiles.csv')
            h0_profiles = df[df['profile_id'] == 'H0']

            self.h0_profiles = {}
            for period in ['winter', 'summer', 'transition']:
                for day in ['workday', 'saturday', 'sunday']:
                    mask = (h0_profiles['period'] == period) & (h0_profiles['day'] == day)
                    profile_values = h0_profiles[mask]['watts'].tolist()

                    if not profile_values:
                        raise ValueError(f"Keine Daten für {period}_{day}")

                    self.h0_profiles[f"{period}_{day}"] = profile_values

            logger.info("BDEW-Profile erfolgreich geladen")
        except Exception as e:
            logger.error(f"Fehler beim Laden der BDEW-Profile: {str(e)}")
            raise

    def calculate_h0_dynamic_factor(self, date):
        """Berechnet den H0-Dynamikfaktor nach BDEW-Polynom"""
        day_of_year = date.timetuple().tm_yday

        # BDEW Polynom-Koeffizienten
        a = -3.92e-10
        b = 3.20e-7
        c = -7.02e-5
        d = 2.10e-3
        e = 1.24

        factor = (a * day_of_year ** 4 + b * day_of_year ** 3 +
                  c * day_of_year ** 2 + d * day_of_year + e)

        logger.debug(f"Dynamikfaktor für {date.date()}: {factor:.4f}")
        return factor

    def calculate_yearly_consumption(self, building_id):
        """Berechnet den Jahresverbrauch basierend auf der Haushaltsverteilung"""

        household_info = self.household_data.get(building_id)
        if not household_info:
            raise ValueError(f"Keine Haushaltsdaten für Gebäude {building_id}")

        total_consumption = 0
        household_details = []

        for household in household_info.get("Haushaltsverteilung", []):
            residents = household.get("einwohner", 1)

            # BDEW Verbrauchswerte
            if residents == 1:
                consumption = 1900
            elif residents == 2:
                consumption = 2890
            elif residents == 3:
                consumption = 3720
            elif residents == 4:
                consumption = 4085
            else:  # 5 oder mehr
                consumption = 5430
                additional_residents = max(0, residents - 5)
                consumption += additional_residents * 1020

            total_consumption += consumption
            household_details.append({
                'residents': residents,
                'consumption': consumption
            })

        logger.info(f"Gebäude {building_id} - Berechneter Jahresverbrauch: {total_consumption} kWh")
        for detail in household_details:
            logger.debug(f"Haushalt mit {detail['residents']} Personen: {detail['consumption']} kWh/Jahr")

        return total_consumption, household_details

    def generate_load_profile(self, building_id, start_date, end_date):
        """Generiert das Lastprofil für ein Wohngebäude"""
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")

        # Berechne Skalierungsfaktor
        building = self.building_data.get(building_id)
        if building and building.get("Gebaeudecode") == "2512":  # Pumpstation
            yearly_consumption = 45000
        else:
            yearly_consumption, _ = self.calculate_yearly_consumption(building_id)

        scaling_factor = yearly_consumption / 1000  # Normierung auf Basis-Lastprofil

        profile_data = []
        current_date = start_date

        # Tracking für Validierung
        period_consumption = {
            'winter': 0,
            'summer': 0,
            'transition': 0
        }

        while current_date <= end_date:
            period = self.seasonal.get_period(current_date)
            day_type = self.seasonal.get_day_type(current_date)
            profile_key = f"{period}_{day_type}"

            base_time = datetime.combine(current_date, datetime.min.time())
            daily_consumption = 0

            for i in range(96):
                timestamp = base_time + timedelta(minutes=15 * i)
                base_load = self.h0_profiles[profile_key][i]  # In Watt

                # Dynamikfaktor anwenden
                dynamic_factor = self.calculate_h0_dynamic_factor(timestamp)

                # Erst in kW umrechnen, dann skalieren und Dynamikfaktor anwenden
                power_kw = (base_load / 1000) * scaling_factor * dynamic_factor

                daily_consumption += power_kw * 0.25  # kWh pro 15-Minuten-Intervall

                profile_data.append({
                    'timestamp': timestamp,
                    'power_kw': power_kw,
                    'period': period,
                    'day_type': day_type,
                    'dynamic_factor': dynamic_factor
                })

            period_consumption[period] += daily_consumption
            current_date += timedelta(days=1)

        # Logging der Periodenverbräuche
        total_consumption = sum(period_consumption.values())
        for period, consumption in period_consumption.items():
            percentage = (consumption / total_consumption) * 100
            logger.info(f"Periode {period}: {consumption:.2f} kWh ({percentage:.1f}%)")

        return pd.DataFrame(profile_data)

    def generate_profiles_for_all_buildings(self, start_date, end_date):
        """Generiert Profile für alle Wohngebäude"""
        results = {}
        logger.info(f"Starte Profilgenerierung für {len(self.residential_buildings)} Gebäude")

        for building_id in self.residential_buildings:
            try:
                logger.info(f"Generiere Profil für Gebäude {building_id}")
                profile = self.generate_load_profile(building_id, start_date, end_date)
                yearly_consumption, household_details = self.calculate_yearly_consumption(building_id)

                results[building_id] = {
                    'profile': profile,
                    'yearly_consumption': yearly_consumption,
                    'household_details': household_details,
                    'building_type': self.residential_buildings[building_id]['Gebaeudefunktion'],
                    'households': self.household_data[building_id]['BerechneteHaushalte'],
                    'residents': self.household_data[building_id]['BerechneteEinwohner']
                }

                logger.info(f"Profil für Gebäude {building_id} erfolgreich generiert")

            except Exception as e:
                logger.error(f"Fehler bei Gebäude {building_id}: {str(e)}")
                logger.error(f"Gebäude in building_data: {building_id in self.building_data}")
                logger.error(f"Gebäude in household_data: {building_id in self.household_data}")

        return results

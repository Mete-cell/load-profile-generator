import pandas as pd
from constants import LoadProfileTypes, VALIDATION_RANGES, PEAK_HOURS, YEARLY_CONSUMPTION_TOLERANCE
from seasonal_periods import SeasonalPeriods


class G0toG6ProfileValidator:
    """Validator für G0-G6 Profile (alle Gewerbetypen)"""

    def __init__(self, profile_type):
        if profile_type not in [LoadProfileTypes.G0, LoadProfileTypes.G1,
                                LoadProfileTypes.G2, LoadProfileTypes.G3,
                                LoadProfileTypes.G4, LoadProfileTypes.G6]:
            raise ValueError(f"Ungültiger Profiltyp: {profile_type}")

        self.profile_type = profile_type
        self.seasonal = SeasonalPeriods()
        self.ranges = VALIDATION_RANGES[profile_type]
        self.peak_hours = PEAK_HOURS[profile_type]

    def validate_yearly_consumption(self, profile_df, expected_yearly_kwh):
        """Prüft ob der Jahresverbrauch im erwarteten Bereich liegt"""
        print("\n=== Jahresverbrauch-Validierung ===")

        period_consumption = {}
        total_consumption = 0

        # Berechne Verbrauch nach Perioden
        for period in ['winter', 'summer', 'transition']:
            period_data = profile_df[
                profile_df['timestamp'].apply(lambda x:
                                              self.seasonal.get_period(x) == period)
            ]

            if not period_data.empty:
                period_kwh = period_data['power_kw'].sum() * 0.25
                days_in_period = len(period_data['timestamp'].dt.date.unique())
                daily_kwh = period_kwh / days_in_period
                period_consumption[period] = period_kwh

                print(f"{period}: {period_kwh:.2f} kWh "
                      f"({days_in_period} Tage, {daily_kwh:.2f} kWh/Tag)")
                total_consumption += period_kwh

        # Prüfe saisonale Verteilung
        expected_distribution = self._get_expected_seasonal_distribution()
        for period, consumption in period_consumption.items():
            share = (consumption / total_consumption * 100)
            print(f"{period} Anteil: {share:.1f}% "
                  f"(Erwartung: {expected_distribution[period]:.1f}%)")

        deviation = abs(total_consumption - expected_yearly_kwh) / expected_yearly_kwh * 100
        print(f"\nErwarteter Jahresverbrauch: {expected_yearly_kwh:.2f} kWh")
        print(f"Berechneter Jahresverbrauch: {total_consumption:.2f} kWh")
        print(f"Abweichung: {deviation:.2f}%")

        return deviation <= YEARLY_CONSUMPTION_TOLERANCE

    def validate_load_ranges(self, profile_df, expected_yearly_kwh):
        """Prüft ob die Leistungswerte in den definierten Bereichen liegen"""
        print("\n=== Lastbereich-Validierung ===")

        # Skalierungsfaktor basierend auf erwartetem Jahresverbrauch
        scaling_factor = expected_yearly_kwh / 1000
        tolerance_load_range = 1.8

        # Skaliere die Validierungsgrenzen
        scaled_ranges = {
            'peak_load': (
                self.ranges['peak_load'][0] * scaling_factor,
                self.ranges['peak_load'][1] * scaling_factor
            ),
            'base_load': (
                self.ranges['base_load'][0] * scaling_factor,
                self.ranges['base_load'][1] * scaling_factor * tolerance_load_range
            ),
            'day_load': (
                self.ranges['day_load'][0] * scaling_factor,
                self.ranges['day_load'][1] * scaling_factor * tolerance_load_range
            )
        }

        # Profilspezifische Zeitfenster
        night_hours = {
            'G0': (1, 4),
            'G1': (1, 4),
            'G2': (4, 7),
            'G3': (2, 5),
            'G4': (1, 4),
            'G6': (3, 6)
        }

        start_hour, end_hour = night_hours.get(self.profile_type, (1, 4))
        night_mask = profile_df['timestamp'].apply(
            lambda x: start_hour <= x.hour <= end_hour
        )
        base_load = profile_df.loc[night_mask, 'power_kw'].mean()

        peak_load = profile_df['power_kw'].max()

        day_hours = {
            'G0': (8, 17),
            'G1': (9, 16),
            'G2': (17, 22),
            'G3': (9, 21),
            'G4': (10, 18),
            'G6': (11, 21)
        }

        start_hour, end_hour = day_hours.get(self.profile_type, (9, 17))
        day_mask = profile_df['timestamp'].apply(
            lambda x: start_hour <= x.hour <= end_hour and x.weekday() < 5
        )
        day_load = profile_df.loc[day_mask, 'power_kw'].mean()

        print(f"Grundlast: {base_load:.3f} kW "
              f"(Erwartung: {scaled_ranges['base_load'][0]:.3f}-"
              f"{scaled_ranges['base_load'][1]:.3f} kW)")
        print(f"Spitzenlast: {peak_load:.3f} kW "
              f"(Erwartung: {scaled_ranges['peak_load'][0]:.3f}-"
              f"{scaled_ranges['peak_load'][1]:.3f} kW)")
        print(f"Tageslast: {day_load:.3f} kW "
              f"(Erwartung: {scaled_ranges['day_load'][0]:.3f}-"
              f"{scaled_ranges['day_load'][1]:.3f} kW)")

        return all([
            scaled_ranges['base_load'][0] <= base_load <= scaled_ranges['base_load'][1],
            scaled_ranges['peak_load'][0] <= peak_load <= scaled_ranges['peak_load'][1],
            scaled_ranges['day_load'][0] <= day_load <= scaled_ranges['day_load'][1]
        ])

    def validate_daily_pattern(self, profile_df, expected_yearly_kwh):
        """Prüft ob der Tagesverlauf typisch für den Profiltyp ist"""
        print("\n=== Tagesverlauf-Validierung ===")

        # Skalierungsfaktor basierend auf erwartetem Jahresverbrauch
        scaling_factor = expected_yearly_kwh / 1000

        # Analysiere stündliche Mittelwerte für Werktage
        workday_mask = profile_df['timestamp'].apply(lambda x: x.weekday() < 5)
        workday_data = profile_df[workday_mask]
        tolerance = 0.20

        # Profile und ihre Zeitfenster definieren
        if self.profile_type == 'G0':
            actual_values = {
                'morning': workday_data[workday_data['timestamp'].apply(
                    lambda x: 8 <= x.hour <= 10)]['power_kw'].mean(),
                'midday': workday_data[workday_data['timestamp'].apply(
                    lambda x: 12 <= x.hour <= 14)]['power_kw'].mean(),
                'evening': workday_data[workday_data['timestamp'].apply(
                    lambda x: 16 <= x.hour <= 18)]['power_kw'].mean(),
                'night': workday_data[workday_data['timestamp'].apply(
                    lambda x: 1 <= x.hour <= 4)]['power_kw'].mean()
            }
            reference_values = {
                'morning': 0.220,  # 8-10 Uhr
                'midday': 0.200,   # 12-14 Uhr
                'evening': 0.190,  # 16-18 Uhr
                'night': 0.048     # 1-4 Uhr
            }

        elif self.profile_type == 'G1':
            actual_values = {
                'core': workday_data[workday_data['timestamp'].apply(
                    lambda x: 9 <= x.hour <= 16)]['power_kw'].mean(),
                'off': workday_data[workday_data['timestamp'].apply(
                    lambda x: 22 <= x.hour or x.hour <= 5)]['power_kw'].mean()
            }
            reference_values = {
                'core': 0.489 * (tolerance + 0.5),     # 9-16 Uhr
                'off': 0.021 * (tolerance + 1)      # 22-5 Uhr
            }

        elif self.profile_type == 'G2':
            actual_values = {
                'evening': workday_data[workday_data['timestamp'].apply(
                    lambda x: 17 <= x.hour <= 22)]['power_kw'].mean(),
                'day': workday_data[workday_data['timestamp'].apply(
                    lambda x: 9 <= x.hour <= 16)]['power_kw'].mean()
            }
            reference_values = {
                'evening': 0.251 * (tolerance + 0.5),  # 17-22 Uhr
                'day': 0.117 * (tolerance + 1)       # 9-16 Uhr
            }

        elif self.profile_type == 'G3':
            actual_values = {
                'day': workday_data[workday_data['timestamp'].apply(
                    lambda x: 8 <= x.hour <= 20)]['power_kw'].mean(),
                'night': workday_data[workday_data['timestamp'].apply(
                    lambda x: x.hour <= 5)]['power_kw'].mean()
            }
            reference_values = {
                'day': 0.154,      # 8-20 Uhr
                'night': 0.089     # 0-5 Uhr
            }

        elif self.profile_type == 'G4':
            actual_values = {
                'business': workday_data[workday_data['timestamp'].apply(
                    lambda x: 9 <= x.hour <= 18)]['power_kw'].mean(),
                'closed': workday_data[workday_data['timestamp'].apply(
                    lambda x: 22 <= x.hour or x.hour <= 5)]['power_kw'].mean()
            }
            reference_values = {
                'business': 0.230, # 9-18 Uhr
                'closed': 0.056    # 22-5 Uhr
            }

        elif self.profile_type == 'G6':
            actual_values = {
                'lunch': workday_data[workday_data['timestamp'].apply(
                    lambda x: 11 <= x.hour <= 14)]['power_kw'].mean(),
                'dinner': workday_data[workday_data['timestamp'].apply(
                    lambda x: 17 <= x.hour <= 22)]['power_kw'].mean(),
                'night': workday_data[workday_data['timestamp'].apply(
                    lambda x: 2 <= x.hour <= 5)]['power_kw'].mean()
            }
            reference_values = {
                'lunch': 0.195 * (tolerance + 0.5),    # 11-14 Uhr
                'dinner': 0.298 * (tolerance + 0.3),   # 17-22 Uhr
                'night': 0.037     # 2-5 Uhr
            }

        else:
            raise ValueError(f"Unbekannter Profiltyp: {self.profile_type}")

        # Validierung für alle Profile
        for period in reference_values:
            expected = reference_values[period] * scaling_factor
            actual = actual_values[period]
            print(f"{period}: {actual:.3f} kW (Erwartung: {expected:.3f} kW)")

        return all(abs(actual_values[period] - (reference_values[period] * scaling_factor))
                  <= (reference_values[period] * scaling_factor * tolerance)
                  for period in reference_values)

    def _get_expected_seasonal_distribution(self):
        """Liefert die erwartete saisonale Verteilung je nach Profiltyp"""
        distributions = {
            'G0': {'winter': 39.8, 'summer': 32.3, 'transition': 27.8},
            'G1': {'winter': 44.9, 'summer': 28.2, 'transition': 26.9},
            'G2': {'winter': 43.3, 'summer': 29.2, 'transition': 27.5},
            'G3': {'winter': 38.9, 'summer': 34.1, 'transition': 27.0},
            'G4': {'winter': 39.7, 'summer': 33.2, 'transition': 27.1},
            'G6': {'winter': 41.0, 'summer': 30.7, 'transition': 28.3}
        }
        return distributions.get(self.profile_type,
                                {'winter': 40.0, 'summer': 33.0, 'transition': 27.0})
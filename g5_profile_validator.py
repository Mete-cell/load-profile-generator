import pandas as pd
from constants import LoadProfileTypes, VALIDATION_RANGES, PEAK_HOURS, YEARLY_CONSUMPTION_TOLERANCE
from seasonal_periods import SeasonalPeriods


class G5ProfileValidator:
    """Validator für G5-Profile (Bäckereien)"""

    def __init__(self):
        self.seasonal = SeasonalPeriods()
        # Spezifische Ranges für G5 basierend auf der BDEW-Analyse
        self.ranges = {
            'peak_load': (0.220, 0.260),   # Max: ~244.70W ±6%
            'base_load': (0.035, 0.045),   # Min: ~40.10W ±12%
            'day_load': (0.115, 0.135)     # Durchschnitt: ~125.45W ±8%
        }
        self.peak_hours = [(4, 8)]  # Hauptbackzeit früh morgens

    def validate_yearly_consumption(self, profile_df, expected_yearly_kwh):
        """Prüft ob der Jahresverbrauch im erwarteten Bereich liegt"""
        print("\n=== Jahresverbrauch-Validierung (G5) ===")

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
        for period, consumption in period_consumption.items():
            share = (consumption / total_consumption * 100)
            print(f"{period} Anteil: {share:.1f}%")

        deviation = abs(total_consumption - expected_yearly_kwh) / expected_yearly_kwh * 100
        print(f"\nErwarteter Jahresverbrauch: {expected_yearly_kwh:.2f} kWh")
        print(f"Berechneter Jahresverbrauch: {total_consumption:.2f} kWh")
        print(f"Abweichung: {deviation:.2f}%")

        return deviation <= YEARLY_CONSUMPTION_TOLERANCE

    def validate_load_ranges(self, profile_df, expected_yearly_kwh):
        """Prüft ob die Leistungswerte in den definierten Bereichen liegen"""
        print("\n=== Lastbereich-Validierung ===")

        scaling_factor = expected_yearly_kwh / 1000
        tolerance_load_range = 1.9

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

        # Spezifische Zeitfenster für Bäckerei
        night_mask = profile_df['timestamp'].apply(lambda x: 1 <= x.hour <= 3)
        base_load = profile_df.loc[night_mask, 'power_kw'].mean()

        peak_load = profile_df['power_kw'].max()

        # Hauptgeschäftszeit
        day_mask = profile_df['timestamp'].apply(
            lambda x: 6 <= x.hour <= 18 and x.weekday() < 6
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
        """Prüft ob der Tagesverlauf typisch für eine Bäckerei ist"""
        print("\n=== Tagesverlauf-Validierung ===")

        scaling_factor = expected_yearly_kwh / 1000

        # Analysiere stündliche Mittelwerte für Werktage
        workday_mask = profile_df['timestamp'].apply(lambda x: x.weekday() < 6)
        workday_data = profile_df[workday_mask]

        # Charakteristische Zeiten für Bäckerei
        actual_values = {
            'early_morning': workday_data[workday_data['timestamp'].apply(
                lambda x: 4 <= x.hour <= 7)]['power_kw'].mean(),
            'morning': workday_data[workday_data['timestamp'].apply(
                lambda x: 8 <= x.hour <= 11)]['power_kw'].mean(),
            'afternoon': workday_data[workday_data['timestamp'].apply(
                lambda x: 14 <= x.hour <= 17)]['power_kw'].mean(),
            'night': workday_data[workday_data['timestamp'].apply(
                lambda x: 1 <= x.hour <= 3)]['power_kw'].mean()
        }

        # Referenzwerte für Bäckerei
        reference_values = {
            'early_morning': 240.0,  # Hauptbackzeit
            'morning': 180.0,        # Hauptverkaufszeit
            'afternoon': 120.0,      # Nachmittagsgeschäft
            'night': 100.0           # Nachtgrundlast
        }

        for period in reference_values:
            expected = (reference_values[period] * scaling_factor) / 1000
            actual = actual_values[period]
            print(f"{period}: {actual:.3f} kW (Erwartung: {expected:.3f} kW)")

        tolerance = 0.2  # 20% Toleranz
        return all(abs(actual_values[period] - ((reference_values[period] * scaling_factor) / 1000))
                  <= ((reference_values[period] * scaling_factor) / 1000) * tolerance
                  for period in reference_values)
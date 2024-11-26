import pandas as pd
from constants import LoadProfileTypes, VALIDATION_RANGES, PEAK_HOURS, YEARLY_CONSUMPTION_TOLERANCE
from seasonal_periods import SeasonalPeriods


class MixedH0G0ProfileValidator:
    """Validator für gemischte H0/G0-Profile"""

    def __init__(self):
        self.seasonal = SeasonalPeriods()
        self.ranges = VALIDATION_RANGES[LoadProfileTypes.MIXED]
        self.peak_hours = PEAK_HOURS[LoadProfileTypes.MIXED]

    def validate_yearly_consumption(self, profile_df, expected_yearly_kwh):
        """
        Prüft ob der Jahresverbrauch im erwarteten Bereich liegt.

        Args:
            profile_df (pd.DataFrame): Lastprofil
            expected_yearly_kwh (dict): Erwarteter Jahresverbrauch {'h0': value, 'g0': value}

        Returns:
            bool: True wenn Verbrauch im Toleranzbereich
        """
        actual_consumption = 0
        print("\n=== Jahresverbrauch-Validierung (Mixed H0/G0) ===")

        # Berechne Verbrauch nach Perioden
        for period in ['winter', 'summer', 'transition']:
            period_data = profile_df[
                profile_df['timestamp'].apply(lambda x:
                                              self.seasonal.get_period(x) == period)
            ]

            if not period_data.empty:
                period_kwh = period_data['power_kw'].sum() * 0.25
                print(f"{period}: {period_kwh:.2f} kWh")
                actual_consumption += period_kwh

        # Berechne Gesamterwartung (H0 + G0)
        total_expected = expected_yearly_kwh['h0'] + expected_yearly_kwh['g0']

        deviation = abs(actual_consumption - total_expected) / total_expected * 100
        print(f"\nErwarteter Jahresverbrauch H0: {expected_yearly_kwh['h0']:.2f} kWh")
        print(f"Erwarteter Jahresverbrauch G0: {expected_yearly_kwh['g0']:.2f} kWh")
        print(f"Erwarteter Gesamtverbrauch: {total_expected:.2f} kWh")
        print(f"Berechneter Jahresverbrauch: {actual_consumption:.2f} kWh")
        print(f"Abweichung: {deviation:.2f}%")

        return deviation <= YEARLY_CONSUMPTION_TOLERANCE

    def validate_load_ranges(self, profile_df, expected_yearly_kwh):
        """
        Prüft ob die Leistungswerte in den definierten Bereichen liegen.

        Args:
            profile_df (pd.DataFrame): Lastprofil
            expected_yearly_kwh (dict): Erwarteter Jahresverbrauch {'h0': value, 'g0': value}

        Returns:
            bool: True wenn alle Werte in den erwarteten Bereichen
        """
        print("\n=== Lastbereich-Validierung ===")

        # Gesamter erwarteter Jahresverbrauch für Skalierung
        total_expected = expected_yearly_kwh['h0'] + expected_yearly_kwh['g0']
        scaling_factor = total_expected / 1000
        tolerance_load_range = 1.3  # Gleiche Toleranz wie bei anderen Profilen

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

        peak_load = profile_df['power_kw'].max()
        print(f"Spitzenlast: {peak_load:.2f} kW "
              f"(Erwartung: {scaled_ranges['peak_load'][0]:.2f}-"
              f"{scaled_ranges['peak_load'][1]:.2f} kW)")

        # Grundlast (nachts)
        night_mask = profile_df['timestamp'].apply(lambda x: 1 <= x.hour <= 4)
        base_load = profile_df.loc[night_mask, 'power_kw'].mean()
        print(f"Grundlast: {base_load:.2f} kW "
              f"(Erwartung: {scaled_ranges['base_load'][0]:.2f}-"
              f"{scaled_ranges['base_load'][1]:.2f} kW)")

        # Tageslast (9-16 Uhr)
        day_mask = profile_df['timestamp'].apply(lambda x: 9 <= x.hour <= 16)
        day_load = profile_df.loc[day_mask, 'power_kw'].mean()
        print(f"Tageslast: {day_load:.2f} kW "
              f"(Erwartung: {scaled_ranges['day_load'][0]:.2f}-"
              f"{scaled_ranges['day_load'][1]:.2f} kW)")

        return (
                scaled_ranges['base_load'][0] <= base_load <= scaled_ranges['base_load'][1] and
                scaled_ranges['peak_load'][0] <= peak_load <= scaled_ranges['peak_load'][1] and
                scaled_ranges['day_load'][0] <= day_load <= scaled_ranges['day_load'][1]
        )

    def validate_daily_pattern(self, profile_df, expected_yearly_kwh):
        """
        Prüft ob der Tagesverlauf dem erwarteten Muster entspricht.

        Args:
            profile_df (pd.DataFrame): Lastprofil
            expected_yearly_kwh (dict): Erwarteter Jahresverbrauch {'h0': value, 'g0': value}

        Returns:
            bool: True wenn Tagesverlauf plausibel
        """
        print("\n=== Tagesverlauf-Validierung ===")

        # Gesamter erwarteter Jahresverbrauch für Skalierung
        total_expected = expected_yearly_kwh['h0'] + expected_yearly_kwh['g0']
        scaling_factor = total_expected / 1000

        # Analysiere stündliche Mittelwerte für Werktage
        workday_mask = profile_df['timestamp'].apply(lambda x: x.weekday() < 5)
        workday_data = profile_df[workday_mask]

        # Charakteristische Zeiten für gemischtes Profil
        actual_values = {
            'morning': workday_data[workday_data['timestamp'].apply(
                lambda x: 7 <= x.hour <= 9)]['power_kw'].mean(),
            'business': workday_data[workday_data['timestamp'].apply(
                lambda x: 9 <= x.hour <= 17)]['power_kw'].mean(),
            'evening': workday_data[workday_data['timestamp'].apply(
                lambda x: 17 <= x.hour <= 21)]['power_kw'].mean(),
            'night': workday_data[workday_data['timestamp'].apply(
                lambda x: 1 <= x.hour <= 4)]['power_kw'].mean()
        }

        # Referenzwerte für Mischprofil
        reference_values = {
            'morning': 180.0,  # Morgenpeak (H0 + G0)
            'business': 200.0,  # Geschäftszeit
            'evening': 170.0,  # Abendpeak (hauptsächlich H0)
            'night': 45.0  # Nachts (Grundlast)
        }

        for period in reference_values:
            expected = (reference_values[period] * scaling_factor) / 1000  # W zu kW
            actual = actual_values[period]
            print(f"{period}: {actual:.3f} kW (Erwartung: {expected:.3f} kW)")

        return all(abs(actual_values[period] - ((reference_values[period] * scaling_factor) / 1000))
                   <= ((reference_values[period] * scaling_factor) / 1000)
                   for period in reference_values)

    def validate_weekend_pattern(self, profile_df):
        """
        Prüft das Wochenendverhalten des gemischten Profils.

        Args:
            profile_df (pd.DataFrame): Lastprofil

        Returns:
            dict: Validierungsergebnisse
        """
        print("\n=== Wochenendverhalten-Validierung ===")

        # Separate Masken für verschiedene Tage
        workday_mask = profile_df['timestamp'].apply(lambda x: x.weekday() < 5)
        saturday_mask = profile_df['timestamp'].apply(lambda x: x.weekday() == 5)
        sunday_mask = profile_df['timestamp'].apply(lambda x: x.weekday() == 6)

        # Durchschnittliche Lasten
        workday_avg = profile_df[workday_mask]['power_kw'].mean()
        saturday_avg = profile_df[saturday_mask]['power_kw'].mean()
        sunday_avg = profile_df[sunday_mask]['power_kw'].mean()

        # Erwartete Verhältnisse für gemischtes Profil:
        # Samstag: ~70-90% der Werktage (Mix aus reduziertem Gewerbe und normalem Haushalt)
        # Sonntag: ~50-70% der Werktage (hauptsächlich Haushaltslast)
        sat_ratio = saturday_avg / workday_avg
        sun_ratio = sunday_avg / workday_avg

        print(f"Durchschnittslast Werktag: {workday_avg:.3f} kW")
        print(f"Durchschnittslast Samstag: {saturday_avg:.3f} kW")
        print(f"Durchschnittslast Sonntag: {sunday_avg:.3f} kW")
        print(f"Verhältnis Samstag/Werktag: {sat_ratio:.2%}")
        print(f"Verhältnis Sonntag/Werktag: {sun_ratio:.2%}")

        is_valid_saturday = 0.7 <= sat_ratio <= 0.9
        is_valid_sunday = 0.5 <= sun_ratio <= 0.7

        return {
            'workday_avg': workday_avg,
            'saturday_avg': saturday_avg,
            'sunday_avg': sunday_avg,
            'sat_ratio': sat_ratio,
            'sun_ratio': sun_ratio,
            'is_valid': is_valid_saturday and is_valid_sunday
        }
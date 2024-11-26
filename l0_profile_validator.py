import pandas as pd
from constants import LoadProfileTypes, VALIDATION_RANGES, PEAK_HOURS, YEARLY_CONSUMPTION_TOLERANCE
from seasonal_periods import SeasonalPeriods


class L0ProfileValidator:
    """Validator für L0-Profile (Landwirtschaftliche Gebäude)"""

    def __init__(self):
        self.seasonal = SeasonalPeriods()
        self.ranges = VALIDATION_RANGES[LoadProfileTypes.L0]
        self.peak_hours = PEAK_HOURS[LoadProfileTypes.L0]

    def validate_yearly_consumption(self, profile_df, expected_yearly_kwh, building_code=None):
        """Prüft ob der Jahresverbrauch im erwarteten Bereich liegt"""
        print("\n=== Jahresverbrauch-Validierung (L0) ===")

        period_consumption = {}
        total_consumption = 0

        # Berechne Verbrauch nach Perioden
        for period in ['winter', 'summer', 'transition']:
            period_data = profile_df[
                profile_df['timestamp'].apply(lambda x:
                                              self.seasonal.get_period(x) == period)
            ]

            if not period_data.empty:
                # Berechne den tatsächlichen Verbrauch für die Periode
                # power_kw * 0.25 gibt die kWh pro 15-Minuten-Intervall
                period_kwh = period_data['power_kw'].sum() * 0.25
                period_consumption[period] = period_kwh
                print(f"{period}: {period_kwh:.2f} kWh")
                total_consumption += period_kwh

        # Gebäudetypspezifische Toleranz
        tolerance = YEARLY_CONSUMPTION_TOLERANCE
        if building_code:
            if building_code == "2724":  # Stall
                tolerance *= 1.2  # Höhere Toleranz wegen Melkzeiten
            elif building_code == "2740":  # Gewächshaus
                tolerance *= 1.3  # Höhere Toleranz wegen Beleuchtung/Klimatisierung

        deviation = abs(total_consumption - expected_yearly_kwh) / expected_yearly_kwh * 100
        print(f"\nErwarteter Jahresverbrauch: {expected_yearly_kwh:.2f} kWh")
        print(f"Berechneter Jahresverbrauch: {total_consumption:.2f} kWh")
        print(f"Abweichung: {deviation:.2f}% (Toleranz: ±{tolerance:.1f}%)")

        return deviation <= tolerance

    def validate_load_ranges(self, profile_df, expected_yearly_kwh, building_code=None):
        """Prüft ob die Leistungswerte in den definierten Bereichen liegen."""
        print("\n=== Lastbereich-Validierung ===")

        # Skalierungsfaktor basierend auf erwartetem Jahresverbrauch
        scaling_factor = expected_yearly_kwh / 1000.0

        # Skaliere die Basis-Validierungsgrenzen mit dem gleichen Faktor
        scaled_ranges = {
            'peak_load': (
                self.ranges['peak_load'][0] * scaling_factor,
                self.ranges['peak_load'][1] * scaling_factor
            ),
            'base_load': (
                self.ranges['base_load'][0] * scaling_factor,
                self.ranges['base_load'][1] * scaling_factor
            ),
            'day_load': (
                self.ranges['day_load'][0] * scaling_factor,
                self.ranges['day_load'][1] * scaling_factor
            )
        }

        # Gebäudespezifische Anpassungen
        if building_code:
            if building_code == "2724":  # Stall
                # Höhere Spitzenlast während Melkzeiten
                scaled_ranges['peak_load'] = (
                    scaled_ranges['peak_load'][0] * 1.2,
                    scaled_ranges['peak_load'][1] * 1.2
                )
            elif building_code == "2740":  # Gewächshaus
                # Höhere Grundlast durch Klimatisierung
                scaled_ranges['base_load'] = (
                    scaled_ranges['base_load'][0] * 1.3,
                    scaled_ranges['base_load'][1] * 1.3
                )

        peak_load = profile_df['power_kw'].max()
        print(f"Spitzenlast: {peak_load:.2f} kW "
              f"(Erwartung: {scaled_ranges['peak_load'][0]:.2f}-"
              f"{scaled_ranges['peak_load'][1]:.2f} kW)")

        # Grundlast (frühe Morgenstunden)
        night_mask = profile_df['timestamp'].apply(lambda x: 2 <= x.hour <= 4)
        base_load = profile_df.loc[night_mask, 'power_kw'].mean()
        print(f"Grundlast: {base_load:.2f} kW "
              f"(Erwartung: {scaled_ranges['base_load'][0]:.2f}-"
              f"{scaled_ranges['base_load'][1]:.2f} kW)")

        # Tageslast während Hauptarbeitszeit
        day_mask = profile_df['timestamp'].apply(lambda x: 8 <= x.hour <= 16)
        day_load = profile_df.loc[day_mask, 'power_kw'].mean()
        print(f"Tageslast: {day_load:.2f} kW "
              f"(Erwartung: {scaled_ranges['day_load'][0]:.2f}-"
              f"{scaled_ranges['day_load'][1]:.2f} kW)")

        return (
                scaled_ranges['peak_load'][0] <= peak_load <= scaled_ranges['peak_load'][1] and
                scaled_ranges['base_load'][0] <= base_load <= scaled_ranges['base_load'][1] and
                scaled_ranges['day_load'][0] <= day_load <= scaled_ranges['day_load'][1]
        )

    def validate_daily_pattern(self, profile_df, building_code=None):
        """
        Prüft ob der Tagesverlauf typisch für landwirtschaftliche Nutzung ist.
        Berücksichtigt gebäudespezifische Muster.
        """
        print("\n=== Tagesverlauf-Validierung ===")

        # Analysiere stündliche Mittelwerte für Werktage
        workday_mask = profile_df['timestamp'].apply(lambda x: x.weekday() < 5)
        workday_data = profile_df[workday_mask]
        hourly = workday_data.set_index('timestamp').resample('h')['power_kw'].mean()

        # Gebäudespezifische Validierung
        if building_code == "2724":  # Stall
            # Prüfe Melkzeiten (morgens und abends)
            morning_milking = hourly.between_time('05:00', '07:00').mean()
            evening_milking = hourly.between_time('16:00', '18:00').mean()
            midday_load = hourly.between_time('10:00', '14:00').mean()

            print(f"Morgenlast (Melkzeit): {morning_milking:.2f} kW")
            print(f"Abendlast (Melkzeit): {evening_milking:.2f} kW")
            print(f"Mittagslast: {midday_load:.2f} kW")

            # Prüfe ob Melkzeiten erkennbar sind
            return (morning_milking > midday_load * 1.2 and
                    evening_milking > midday_load * 1.2)

        elif building_code == "2740":  # Gewächshaus
            # Prüfe Beleuchtungszeiten
            early_morning = hourly.between_time('04:00', '07:00').mean()
            evening = hourly.between_time('17:00', '22:00').mean()
            midday = hourly.between_time('10:00', '15:00').mean()

            print(f"Frühmorgenlast: {early_morning:.2f} kW")
            print(f"Abendlast: {evening:.2f} kW")
            print(f"Mittagslast: {midday:.2f} kW")

            # Prüfe ob Beleuchtungsmuster erkennbar
            return (early_morning > midday and evening > midday)

        else:  # Allgemeines landwirtschaftliches Gebäude
            # Prüfe Tagesaktivität
            daytime = hourly.between_time('06:00', '18:00').mean()
            nighttime = hourly.between_time('22:00', '04:00').mean()

            ratio = daytime / nighttime
            print(f"Verhältnis Tag/Nacht: {ratio:.2f}")

            return ratio >= 2.0

    def validate_weekend_pattern(self, profile_df, building_code=None):
        """
        Prüft das Wochenendverhalten von landwirtschaftlichen Gebäuden.
        Berücksichtigt gebäudespezifische Unterschiede.
        """
        print("\n=== Wochenendverhalten-Validierung ===")

        workday_mask = profile_df['timestamp'].apply(lambda x: x.weekday() < 5)
        saturday_mask = profile_df['timestamp'].apply(lambda x: x.weekday() == 5)
        sunday_mask = profile_df['timestamp'].apply(lambda x: x.weekday() == 6)

        workday_avg = profile_df[workday_mask]['power_kw'].mean()
        saturday_avg = profile_df[saturday_mask]['power_kw'].mean()
        sunday_avg = profile_df[sunday_mask]['power_kw'].mean()

        sat_ratio = saturday_avg / workday_avg
        sun_ratio = sunday_avg / workday_avg

        print(f"Durchschnittslast Werktag: {workday_avg:.3f} kW")
        print(f"Durchschnittslast Samstag: {saturday_avg:.3f} kW")
        print(f"Durchschnittslast Sonntag: {sunday_avg:.3f} kW")
        print(f"Verhältnis Samstag/Werktag: {sat_ratio:.2%}")
        print(f"Verhältnis Sonntag/Werktag: {sun_ratio:.2%}")

        # Gebäudespezifische Validierung
        is_valid = False

        if building_code == "2724":  # Stall
            # Stallbetrieb läuft durchgehend (Melken auch am Wochenende)
            is_valid = (0.9 <= sat_ratio <= 1.1 and
                        0.9 <= sun_ratio <= 1.1)
        elif building_code == "2740":  # Gewächshaus
            # Leicht reduzierter Betrieb am Wochenende
            is_valid = (0.7 <= sat_ratio <= 0.9 and
                        0.7 <= sun_ratio <= 0.9)
        else:  # Allgemeines landwirtschaftliches Gebäude
            # Deutlich reduzierter Betrieb am Wochenende
            is_valid = (0.5 <= sat_ratio <= 0.8 and
                        0.4 <= sun_ratio <= 0.7)

        return {
            'workday_avg': workday_avg,
            'saturday_avg': saturday_avg,
            'sunday_avg': sunday_avg,
            'sat_ratio': sat_ratio,
            'sun_ratio': sun_ratio,
            'is_valid': is_valid
        }
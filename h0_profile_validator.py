import pandas as pd
import matplotlib.pyplot as plt
import logging
from seasonal_periods import SeasonalPeriods
from datetime import datetime, timedelta
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class H0ProfileValidator:
    def __init__(self):
        self.seasonal = SeasonalPeriods()
        self.expected_ranges = {
            'peak_load': (0.150, 0.270),
            'base_load': (0.035, 0.065),
            'day_load': (0.090, 0.150),
            'seasonal_distribution': {
                'winter': (0.35, 0.45),
                'summer': (0.25, 0.35),
                'transition': (0.25, 0.35)
            }
        }

    def validate_yearly_consumption(self, profile_df, expected_yearly_kwh):
        """Prüft ob der Jahresverbrauch stimmt"""
        logger.info("\n=== Jahresverbrauch-Validierung ===")

        period_consumption = {}
        total_consumption = 0

        for period in ['winter', 'summer', 'transition']:
            period_data = profile_df[
                profile_df['timestamp'].apply(lambda x:
                                              self.seasonal.get_period(x) == period)
            ]

            if not period_data.empty:
                period_kwh = period_data['power_kw'].sum() * 0.25
                percentage = period_kwh / expected_yearly_kwh

                logger.info(f"Periode {period}: {period_kwh:.2f} kWh ({percentage:.1%})")

                total_consumption += period_kwh

        deviation = abs(total_consumption - expected_yearly_kwh) / expected_yearly_kwh
        logger.info(f"\nErwarteter Jahresverbrauch: {expected_yearly_kwh:.2f} kWh")
        logger.info(f"Berechneter Jahresverbrauch: {total_consumption:.2f} kWh")
        logger.info(f"Abweichung: {deviation:.1%}")

        return deviation < 0.05

    def validate_load_ranges(self, profile_df, expected_yearly_kwh):
        """Prüft ob die Leistungswerte in plausiblen Bereichen liegen"""
        logger.info("\n=== Lastbereich-Validierung ===")

        # Skalierungsfaktor und Toleranz
        scaling_factor = expected_yearly_kwh / 1000
        tolerance_load_range = 1.3

        # Skaliere die Validierungsgrenzen
        scaled_ranges = {
            'peak_load': (
                self.expected_ranges['peak_load'][0] * scaling_factor,
                self.expected_ranges['peak_load'][1] * scaling_factor
            ),
            'base_load': (
                self.expected_ranges['base_load'][0] * scaling_factor,
                self.expected_ranges['base_load'][1] * scaling_factor * tolerance_load_range
            ),
            'day_load': (
                self.expected_ranges['day_load'][0] * scaling_factor,
                self.expected_ranges['day_load'][1] * scaling_factor * tolerance_load_range
            )
        }

        peak_load = profile_df['power_kw'].max()
        night_mask = profile_df['timestamp'].apply(lambda x: 23 <= x.hour or x.hour <= 5)
        base_load = profile_df.loc[night_mask, 'power_kw'].mean()
        day_mask = profile_df['timestamp'].apply(lambda x: 9 <= x.hour <= 17)
        day_load = profile_df.loc[day_mask, 'power_kw'].mean()

        logger.info(f"Spitzenlast: {peak_load:.3f} kW "
                   f"(Erwartung: {scaled_ranges['peak_load'][0]:.3f}-"
                   f"{scaled_ranges['peak_load'][1]:.3f} kW)")
        logger.info(f"Grundlast: {base_load:.3f} kW "
                   f"(Erwartung: {scaled_ranges['base_load'][0]:.3f}-"
                   f"{scaled_ranges['base_load'][1]:.3f} kW)")
        logger.info(f"Tageslast: {day_load:.3f} kW "
                   f"(Erwartung: {scaled_ranges['day_load'][0]:.3f}-"
                   f"{scaled_ranges['day_load'][1]:.3f} kW)")

        peak_valid = scaled_ranges['peak_load'][0] <= peak_load <= scaled_ranges['peak_load'][1]
        base_valid = scaled_ranges['base_load'][0] <= base_load <= scaled_ranges['base_load'][1]
        day_valid = scaled_ranges['day_load'][0] <= day_load <= scaled_ranges['day_load'][1]

        if not all([peak_valid, base_valid, day_valid]):
            logger.warning("Lastbereiche außerhalb der erwarteten Grenzen")

        return all([peak_valid, base_valid, day_valid])

    def validate_daily_pattern(self, profile_df, expected_yearly_kwh):
        """Validiert die typischen Tagesverläufe"""
        logger.info("\n=== Tagesverlauf-Validierung ===")

        # Skalierungsfaktor
        scaling_factor = expected_yearly_kwh / 1000

        valid_days = 0
        total_days = 0

        for date in pd.date_range(profile_df['timestamp'].min().date(),
                                profile_df['timestamp'].max().date()):
            day_data = profile_df[
                profile_df['timestamp'].dt.date == date.date()
            ]

            if day_data.empty:
                continue

            total_days += 1
            hourly = day_data.set_index('timestamp').resample('h')['power_kw'].mean()

            morning_peak_hour = hourly[6:10].idxmax().hour
            evening_peak_hour = hourly[17:22].idxmax().hour

            valid_morning = 6 <= morning_peak_hour <= 10
            valid_evening = 17 <= evening_peak_hour <= 22

            if all([valid_morning, valid_evening]):
                valid_days += 1

        validation_success = valid_days / total_days >= 0.95
        logger.info(f"Tagesverlauf-Validierung: {valid_days} von {total_days} Tagen valid")

        return validation_success

    def perform_comprehensive_validation(self, profile_df, expected_yearly_kwh):
        """Führt alle Validierungen durch und erstellt einen Gesamtbericht"""
        yearly_valid = self.validate_yearly_consumption(profile_df, expected_yearly_kwh)
        ranges_valid = self.validate_load_ranges(profile_df, expected_yearly_kwh)
        pattern_valid = self.validate_daily_pattern(profile_df, expected_yearly_kwh)

        overall_valid = all([yearly_valid, ranges_valid, pattern_valid])

        logger.info("\n=== Gesamtbewertung ===")
        logger.info(f"Jahresverbrauch plausibel: {'✓' if yearly_valid else '✗'}")
        logger.info(f"Lastbereiche plausibel: {'✓' if ranges_valid else '✗'}")
        logger.info(f"Tagesverlauf plausibel: {'✓' if pattern_valid else '✗'}")
        logger.info(f"\nGesamtergebnis: {'✓' if overall_valid else '✗'}")

        return overall_valid
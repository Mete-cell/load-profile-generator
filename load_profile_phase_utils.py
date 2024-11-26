from datetime import datetime
from dataclasses import dataclass
from typing import Tuple, List, Optional


@dataclass
class Phase:
    """Definiert eine Tagesphase"""
    name: str
    start_hour: int
    end_hour: int


@dataclass
class Season:
    """Definiert eine Jahreszeit"""
    name: str
    de_name: str
    months: List[int]


class TimeDefinitions:
    """Zentrale Definitionen für Zeiträume"""

    # Tagesphasen
    PHASES = [
        Phase("nachtphase", 23, 6),
        Phase("morgenspitze", 6, 9),
        Phase("vormittag", 9, 13),
        Phase("nachmittag", 13, 17),
        Phase("abendspitze", 17, 23)
    ]

    # Jahreszeiten
    SEASONS = [
        Season("winter", "winter", [12, 1, 2]),
        Season("summer", "sommer", [6, 7, 8]),
        Season("transition_1", "frühling", [3, 4, 5]),
        Season("transition_2", "herbst", [9, 10, 11])
    ]

    # Tagestypen
    DAY_TYPES = {
        "workday": "werktag",
        "saturday": "samstag",
        "sunday": "sonntag"
    }

    @staticmethod
    def get_season(date: datetime) -> Season:
        """Ermittelt die Jahreszeit für ein Datum"""
        month = date.month
        for season in TimeDefinitions.SEASONS:
            if month in season.months:
                return season
        # Falls wir hier landen, geben wir Winter zurück als Fallback
        return TimeDefinitions.SEASONS[0]  # Winter

    @staticmethod
    def get_day_type(date: datetime) -> Tuple[str, str]:
        """Ermittelt den Tagestyp (englisch, deutsch)"""
        if date.weekday() < 5:
            return "workday", "werktag"
        elif date.weekday() == 5:
            return "saturday", "samstag"
        else:
            return "sunday", "sonntag"

    @staticmethod
    def is_in_phase(hour: int, phase: Phase) -> bool:
        """Prüft ob eine Stunde in einer Phase liegt"""
        if phase.start_hour < phase.end_hour:
            return phase.start_hour <= hour < phase.end_hour
        else:  # Über Mitternacht
            return hour >= phase.start_hour or hour < phase.end_hour
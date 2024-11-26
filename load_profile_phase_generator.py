from typing import Dict, List, Tuple, Optional
import pandas as pd
import multiprocessing as mp
from functools import partial
from tqdm import tqdm
import json
from datetime import datetime

from constants import LoadProfileTypes, BUILDING_CODE_TO_PROFILE
from h0_load_profile_generator import H0LoadProfileGenerator
from y1_load_profile_generator import Y1LoadProfileGenerator
from mixed_h0g0_load_profile_generator import MixedH0G0LoadProfileGenerator
from g0_to_g6_load_profile_generator import G0toG6LoadProfileGenerator
from g5_load_profile_generator import G5LoadProfileGenerator
from l0_load_profile_generator import L0LoadProfileGenerator
from load_profile_phase_utils import TimeDefinitions, Phase, Season

class ParallelLoadProfileGenerator:
    EXCLUDED_BUILDING_CODES = {
        "2523",  # Umformer
        "2580",  # Heizwerk
        "2520",  # Gebäude zur Elektrizitätsversorgung
        "9998",  # Nach Quellenlage nicht zu spezifizieren
        "1610",  # Überdachung (Y0)
        "1290"   # Schornstein (Y0)
    }

    def __init__(self, building_data_file: str, household_data_file: str):
        # Lade Gebäudedaten einmal zu Beginn
        with open(building_data_file, 'r', encoding='utf-8') as f:
            self.building_data = json.load(f)

        self.building_data_file = building_data_file
        self.household_data_file = household_data_file

    def is_valid_building(self, building_id: str, building_data: Dict) -> bool:
        if not isinstance(building_data, dict):
            return False

        building_code = building_data.get('Gebaeudecode')
        if not building_code:
            return False

        if building_code in self.EXCLUDED_BUILDING_CODES:
            print(f"Überspringe Gebäude {building_id} (Code {building_code}): Ausgeschlossener Gebäudetyp")
            return False

        return True

    def process_building(self, building_tuple: Tuple[str, Optional[Dict]]) -> Tuple[str, Optional[Dict]]:
        building_id, building_data = building_tuple

        if not self.is_valid_building(building_id, building_data):
            return building_id, None

        try:
            building_code = building_data.get('Gebaeudecode')
            profile_type = self.determine_profile_type(building_id, building_code)
            generator = self.get_generator(profile_type)

            profile_df = generator.generate_load_profile(
                building_id,
                "2024-01-01",
                "2024-12-31"
            )

            # Extrahiere einzigartige GebäudeteilIDs
            building_parts = []
            for part in building_data.get("Gebaeudeteile", []):
                part_id = part.get("GebaeudeteilID")
                if part_id and part_id != building_id:  # Nur hinzufügen wenn nicht gleich building_id
                    building_parts.append(part_id)

            # Berechne Phasen
            result = {}

            # Füge Gebäudeteile nur hinzu wenn vorhanden
            if building_parts:
                result["gebaeudeteile"] = building_parts

            for season in TimeDefinitions.SEASONS:
                for day_type, de_day in TimeDefinitions.DAY_TYPES.items():
                    season_mask = profile_df['timestamp'].apply(
                        lambda x: x.month in season.months
                    )
                    day_mask = profile_df['timestamp'].apply(
                        lambda x: TimeDefinitions.get_day_type(x)[0] == day_type
                    )
                    df_filtered = profile_df[season_mask & day_mask]

                    for phase in TimeDefinitions.PHASES:
                        key = f"{season.de_name}_{de_day}_{phase.name}"
                        phase_mask = df_filtered['timestamp'].apply(
                            lambda x: TimeDefinitions.is_in_phase(x.hour, phase)
                        )
                        result[key] = round(
                            df_filtered.loc[phase_mask, 'power_kw'].mean(),
                            4
                        )

            return building_id, result

        except Exception as e:
            print(f"Fehler bei Gebäude {building_id}: {str(e)}")
            return building_id, None

    def get_generator(self, profile_type: str):
        if profile_type in ['G0', 'G1', 'G2', 'G3', 'G4', 'G6']:
            return G0toG6LoadProfileGenerator(self.building_data_file)
        elif profile_type == 'G5':
            return G5LoadProfileGenerator(self.building_data_file)
        elif profile_type == 'H0':
            return H0LoadProfileGenerator(self.building_data_file, self.household_data_file)
        elif profile_type == 'Y1':
            return Y1LoadProfileGenerator(self.building_data_file)
        elif profile_type == 'MIXED':
            return MixedH0G0LoadProfileGenerator(self.building_data_file, self.household_data_file)
        elif profile_type == 'L0':
            return L0LoadProfileGenerator(self.building_data_file)
        else:
            raise ValueError(f"Unbekannter Profiltyp: {profile_type}")

    def determine_profile_type(self, building_id: str, building_code: str) -> str:
        if building_code == "2050" and building_id == "DEBBAL520000wboz":
            return 'G5'
        return BUILDING_CODE_TO_PROFILE.get(building_code, 'H0')

    def generate_consumption_statistics(self, output_file: str) -> Dict:
        consumption_stats = {}
        valid_buildings = [
            (id, data) for id, data in self.building_data.items()
            if self.is_valid_building(id, data)
        ]

        print(f"\nBerechne Verbrauchsstatistiken für {len(valid_buildings)} Gebäude...")

        for building_id, building_data in valid_buildings:
            try:
                building_code = building_data.get('Gebaeudecode')
                profile_type = self.determine_profile_type(building_id, building_code)
                generator = self.get_generator(profile_type)

                # Berechne Jahresverbrauch basierend auf Profiltyp
                if profile_type == 'H0':
                    if building_code == "2512":
                        yearly_consumption = 45000
                    else:
                        yearly_consumption, _ = generator.calculate_yearly_consumption(building_id)
                elif profile_type == 'MIXED':
                    # Setze temporäres Flag für Gesamtverbrauch
                    generator._return_total = True
                    yearly_consumption = generator.calculate_yearly_consumption(building_id)
                    # Entferne Flag wieder
                    delattr(generator, '_return_total')
                else:
                    yearly_consumption = generator.calculate_yearly_consumption(building_id)

                area = float(building_data.get("Gesamtnettonutzflaeche", 0))
                specific_consumption = round(yearly_consumption / area, 2) if area > 0 else None

                # Extrahiere einzigartige GebäudeteilIDs
                building_parts = []
                for part in building_data.get("Gebaeudeteile", []):
                    part_id = part.get("GebaeudeteilID")
                    if part_id and part_id != building_id:  # Nur hinzufügen wenn nicht gleich building_id
                        building_parts.append(part_id)

                stats = {
                    "gebaeudefunktion": building_data.get("Gebaeudefunktion", ""),
                    "gebaeudecode": building_code,
                    "profiltyp": profile_type,
                    "nutzflaeche_m2": round(area, 2),
                    "jahresverbrauch_kwh": round(yearly_consumption, 2),
                    "spezifischer_verbrauch_kwh_pro_m2": specific_consumption,
                }

                # Füge Gebäudeteile nur hinzu wenn vorhanden
                if building_parts:
                    stats["gebaeudeteile"] = building_parts

                consumption_stats[building_id] = stats

            except Exception as e:
                print(f"Fehler bei Gebäude {building_id}: {str(e)}")
                continue

        output_consumption_file = output_file.replace('.json', '_verbrauch.json')
        with open(output_consumption_file, 'w', encoding='utf-8') as f:
            json.dump(consumption_stats, f, indent=2, ensure_ascii=False)

        print(f"Verbrauchsstatistiken gespeichert in: {output_consumption_file}")
        return consumption_stats

    def generate_all_profiles(self, output_file: str) -> Dict:
        print(f"Starte Verarbeitung von {len(self.building_data)} Gebäuden...")

        valid_buildings = [
            (id, data) for id, data in self.building_data.items()
            if self.is_valid_building(id, data)
        ]

        print(f"Gefunden: {len(valid_buildings)} gültige Gebäude")

        num_processes = max(1, mp.cpu_count() - 1)
        print(f"Nutze {num_processes} Prozesse")

        with mp.Pool(processes=num_processes) as pool:
            results = list(tqdm(
                pool.imap_unordered(
                    self.process_building,
                    valid_buildings
                ),
                total=len(valid_buildings),
                desc="Verarbeite Gebäude"
            ))

        all_results = {
            building_id: result
            for building_id, result in results
            if result is not None
        }

        print(f"\nSchreibe Ergebnisse in {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        print(f"Fertig. {len(all_results)} Profile generiert.")
        return all_results
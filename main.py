import os
import json
from pathlib import Path
from load_profile_phase_generator import ParallelLoadProfileGenerator


def main():
    # Konfiguration
    BUILDING_DATA_FILE = "output_branitzer_siedlungV11.json"
    HOUSEHOLD_DATA_FILE = "building_population_resultsV6.json"
    OUTPUT_FILE = "gebaeude_lastphasenV2.json"

    # Prüfe ob Eingabedateien existieren
    if not all(Path(f).exists() for f in [BUILDING_DATA_FILE, HOUSEHOLD_DATA_FILE]):
        raise FileNotFoundError("Eingabedateien nicht gefunden")

    print("Initialisiere Generator...")
    generator = ParallelLoadProfileGenerator(BUILDING_DATA_FILE, HOUSEHOLD_DATA_FILE)

    print("\nGeneriere Lastprofile...")
    try:
        results = generator.generate_all_profiles(OUTPUT_FILE)
        print(f"Lastprofile erfolgreich generiert: {len(results)} Gebäudeprofile")
        print(f"Ausgabe gespeichert in: {OUTPUT_FILE}")

        print("\nGeneriere Verbrauchsstatistiken...")
        consumption_stats = generator.generate_consumption_statistics(OUTPUT_FILE)
        print(f"Verbrauchsstatistiken erfolgreich generiert: {len(consumption_stats)} Gebäude")

        # Beispielausgabe
        if results:
            first_building = next(iter(results))
            print(f"\nBeispiel Lastprofil für Gebäude {first_building}:")
            print(json.dumps(results[first_building], indent=2, ensure_ascii=False)[:500] + "...")

            print(f"\nBeispiel Verbrauchsstatistik für Gebäude {first_building}:")
            print(json.dumps(consumption_stats[first_building], indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"Fehler bei der Generierung: {str(e)}")
        raise


if __name__ == "__main__":
    main()
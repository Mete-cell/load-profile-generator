from all_profile_generator.quick_profile_tester import QuickProfileTester


def main():
    tester = QuickProfileTester()

    print("\n=== Detaillierter Test Mischgebäude ===")
    building_id = "DEBBAL520000wbZ3"
    building_code = "1120"

    # Test durchführen
    results = tester.test_single_building(building_id, building_code)

    if results:
        print("\nDetails zum Mischprofil:")
        if isinstance(results.get('yearly_consumption'), dict):
            h0_consumption = results['yearly_consumption'].get('h0', 0)
            g0_consumption = results['yearly_consumption'].get('g0', 0)
            print(f"H0-Anteil: {h0_consumption:.2f} kWh (50%)")
            print(f"G0-Anteil: {g0_consumption:.2f} kWh (50%)")
            print(f"Gesamtverbrauch: {h0_consumption + g0_consumption:.2f} kWh")

        print("\nVerwendete Profile:")
        print("- H0: Haushaltslastprofil (mit Dynamikfaktor)")
        print("- G0: Gewerbe-Standardlastprofil")


if __name__ == "__main__":
    main()
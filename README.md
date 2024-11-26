# BDEW Load Profile Generator

A Python-based tool for generating standardized electrical load profiles based on BDEW (German Association of Energy and Water Industries) standards.

## Features

- Generates 15-minute interval load profiles for different building types:
  - Residential (H0)
  - Commercial (G0-G6)
  - Agricultural (L0)
  - Simple buildings like garages (Y1)
  - Mixed-use properties
- Considers multiple factors:
  - Building type and floor area
  - Day types (workday, Saturday, Sunday)
  - Seasonal variations
  - Special cases (e.g., bakeries, pumping stations)
- Parallel processing for efficient generation
- Validation against BDEW standards
- CSV and JSON export formats

## Requirements

- Python 3.8+
- pandas
- numpy
- tqdm
- multiprocessing

## Installation

```bash
git clone https://github.com/Mete-cell/load-profile-generator.git
cd load-profile-generator
pip install -r requirements.txt
```

## Usage

Basic usage example:

```python
from load_profile_phase_generator import ParallelLoadProfileGenerator

# Initialize generator
generator = ParallelLoadProfileGenerator(
    "building_data.json",
    "household_data.json"
)

# Generate profiles
results = generator.generate_all_profiles("output.json")
```

### Input Data Structure

Building data JSON:
```json
{
    "building_id": {
        "Gebaeudecode": "1000",
        "Gebaeudefunktion": "Wohngebäude",
        "Gesamtnettonutzflaeche": 150.5
    }
}
```

Household data JSON:
```json
{
    "building_id": {
        "BerechneteHaushalte": 2,
        "BerechneteEinwohner": 4,
        "Haushaltsverteilung": [
            {
                "haushalt_nr": 1,
                "einwohner": 2
            }
        ]
    }
}
```

## Output Format

The tool generates two files:
- A CSV file containing the time series data
- A JSON file with metadata including yearly consumption and building information

## Household Consumption Standards

Annual consumption values for residential buildings:
- 1 person: 1900 kWh/year
- 2 persons: 2890 kWh/year
- 3 persons: 3720 kWh/year
- 4 persons: 4085 kWh/year
- 5+ persons: 5430 kWh/year + 1020 kWh for each additional person

## Validation

The tool includes validators for each profile type checking:
- Annual consumption within tolerance
- Load ranges (peak, base, daily loads)
- Typical daily patterns
- Seasonal distribution

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## References

- BDEW Standardized Load Profiles
- German Energy Industry Standards

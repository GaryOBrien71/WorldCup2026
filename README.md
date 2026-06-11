# World Cup 2026 Streamlit Predictor

This is a Streamlit conversion of the uploaded `WorldCup2026.xlsm` workbook.

## What is included

- Interactive group-stage score entry
- Live 12-group standings
- Best third-placed team table
- Player prediction leaderboard using the workbook's player names
- Provisional knockout bracket from the current group tables
- Fixture browser and CSV export
- Save/load app state as JSON
- Original fan-made World Cup-style SVG graphics, colour styling, and team flags

## Notes on the conversion

The workbook had four relevant sheets: `Players`, `Matches R1 - R5`, `Group Stage`, and `Data`.
The app uses the workbook fixtures/groups directly. A few obvious spelling or abbreviation mismatches were normalised so that standings calculate correctly, for example `Ecudor` to `Ecuador`, `Tunisa` to `Tunisia`, `S. Africa` to `South Africa`, and `Saudi A.` to `Saudi Arabia`.

The workbook contained knockout dates but not knockout team mapping. The app therefore generates a provisional 32-team bracket from the group tables: top two in every group plus the best eight third-placed teams.

The included badge, stadium, and trophy are original fan-made graphics for this app. No official FIFA logo is bundled.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Upload this folder to Streamlit Community Cloud, GitHub, or your preferred Python hosting service. The app does not need Excel or macros at runtime because the workbook data has been extracted to CSV/JSON files in the `data/` folder.

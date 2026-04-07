import pandas as pd
import json

files = ["1 Drawer Bedside Table.xlsx", "2 Drawer Dressing Table.xlsx", "3 Drawer Chest.xlsx"]

with open("data_summary.txt", "w", encoding="utf-8") as f:
    for file in files:
        try:
            f.write(f"\nEvaluating file: {file}\n")
            xl = pd.ExcelFile(file)
            f.write(f"Sheets: {xl.sheet_names}\n")
            for sheet in xl.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet, nrows=5)
                f.write(f"  -> Sheet: '{sheet}' Columns:\n")
                for col in df.columns.tolist():
                    f.write(f"    - {col}\n")
                if len(df) > 0:
                    f.write(f"  -> Sample Data (Row 1):\n")
                    for col in df.columns:
                        f.write(f"      {col}: {df.iloc[0][col]}\n")
        except Exception as e:
            f.write(f"Error: {e}\n")

import pandas as pd

file_name = "1 Drawer Bedside Table.xlsx"
print(f"Reading file: {file_name}")

try:
    xl = pd.ExcelFile(file_name)
    sheet_name = xl.sheet_names[0]
    # Read without headers to see raw data layout
    df = pd.read_excel(file_name, sheet_name=sheet_name, header=None, nrows=40)
    
    # Dump to CSV for easy inspection
    df.to_csv("dump.csv", index=False)
    print("Dumped 40 rows to dump.csv")

except Exception as e:
    print("Error:", e)

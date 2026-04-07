import pandas as pd
import numpy as np

file_name = "1 Drawer Bedside Table.xlsx"
print(f"Reading file: {file_name}")

try:
    df = pd.read_excel(file_name, sheet_name=0, header=None)
    
    # Iterate through all cells to find sections
    for row_idx in range(len(df)):
        first_col_val = str(df.iloc[row_idx, 0]).strip()
        second_col_val = str(df.iloc[row_idx, 1]).strip()
        
        # Sometime the Roman Numeral is in col 0, sometimes the whole text is in col 1
        if "NGUYÊN LIỆU" in first_col_val.upper() or "NGUYÊN LIỆU" in second_col_val.upper():
            print(f"\n--- Found NGUYÊN LIỆU at row {row_idx} ---")
            print("Headers at row", row_idx + 1, ":", df.iloc[row_idx + 1].tolist())
            
        if "VẬT TƯ LẮP RÁP" in first_col_val.upper() or "VẬT TƯ LẮP RÁP" in second_col_val.upper() or "PHẦN CỨNG" in first_col_val.upper() or "PHẦN CỨNG" in second_col_val.upper():
            print(f"\n--- Found VẬT TƯ LẮP RÁP at row {row_idx} ---")
            print("Headers at row", row_idx + 1, ":", df.iloc[row_idx + 1].tolist())
            
        if "ĐÓNG GÓI" in first_col_val.upper() or "ĐÓNG GÓI" in second_col_val.upper():
            print(f"\n--- Found VẬT TƯ ĐÓNG GÓI at row {row_idx} ---")
            print("Headers at row", row_idx + 1, ":", df.iloc[row_idx + 1].tolist())

except Exception as e:
    print("Error:", e)

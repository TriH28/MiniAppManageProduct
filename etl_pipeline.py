import pandas as pd
import sqlite3
import unicodedata
import re
import os

def slugify(text):
    if pd.isna(text):
        return ""
    text = str(text)
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[\s_-]+', '-', text)
    return text

def create_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.executescript("""
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS bill_of_materials;
        
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT UNIQUE,
            product_name TEXT
        );
        
        CREATE TABLE bill_of_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            category TEXT,
            material_code TEXT,
            material_name TEXT,
            material_spec TEXT,
            unit TEXT,
            quantity_per_unit REAL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
    """)
    conn.commit()
    return conn

def parse_excel(file_path, conn):
    print(f"Parsing {file_path}...")
    df = pd.read_excel(file_path, sheet_name=0, header=None)
    
    product_name = "Unknown"
    product_code = "Unknown"
    
    for i in range(min(20, len(df))):
        col0 = str(df.iloc[i, 0]).strip()
        col1 = str(df.iloc[i, 1]).strip()
        
        if "Tên sản phẩm" in col0 or "Tên sản phẩm" in col1:
            product_name = str(df.iloc[i, 2]).strip() if not pd.isna(df.iloc[i, 2]) else col1.replace("Tên sản phẩm:", "").strip()
        if "Mã số" in col0 or "Mã số" in col1:
            product_code = str(df.iloc[i, 2]).strip() if not pd.isna(df.iloc[i, 2]) else col1.replace("Mã số:", "").strip()
            if pd.isna(product_code) or product_code == "nan" or product_code == "":
                product_code = str(df.iloc[i, 1]).replace("Mã số:", "").strip()
                
    if product_name == "Unknown":
        product_name = os.path.basename(file_path).replace(".xlsx", "")
    if product_code == "Unknown" or product_code == "" or product_code == "nan":
        product_code = product_name[:5].upper()

    print(f"Found Product: {product_code} - {product_name}")
    
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO products (product_code, product_name) VALUES (?, ?)", (product_code, product_name))
    c.execute("SELECT id FROM products WHERE product_code = ?", (product_code,))
    product_id = c.fetchone()[0]

    current_category = None
    data_rows = []
    
    for i in range(len(df)):
        col0 = str(df.iloc[i, 0]).strip()
        col1 = str(df.iloc[i, 1]).strip()
        col_text = (col0 + " " + col1).upper()
        
        if "NGUYÊN LIỆU" in col_text:
            current_category = "Nguyên Liệu"
            continue
        elif "VẬT TƯ ĐÓNG GÓI" in col_text or "ĐÓNG GÓI" in col_text:
            current_category = "Vật Tư Đóng Gói"
            continue
        elif "VẬT TƯ LẮP RÁP" in col_text or "PHẦN CỨNG" in col_text or "HARDWARE" in col_text:
            current_category = "Vật Tư Lắp Ráp"
            continue
            
        if current_category:
            stt = str(df.iloc[i, 0]).strip()
            if stt == "nan" or stt == "" or stt in ["Stt", "STT"]:
                continue
                
            # Filter Block Headers like "A", "B", Cụm nóc
            if stt.isalpha() and not str(df.iloc[i, 6]).replace(".", "", 1).isdigit():
                continue
                
            try:
                name = str(df.iloc[i, 1]).strip()
                if name == "nan" or name == "": continue
                
                material = str(df.iloc[i, 2]).strip()
                
                if current_category == "Nguyên Liệu":
                    thick = str(df.iloc[i, 3]).strip()
                    width = str(df.iloc[i, 4]).strip()
                    length = str(df.iloc[i, 5]).strip()
                    spec = f"{thick} x {width} x {length}".replace("nan", "0")
                    qty = float(str(df.iloc[i, 6]).strip()) if not pd.isna(df.iloc[i, 6]) else 0
                    unit = "m3" # mặc định
                else:
                    # Packaging / Assembly often has different columns
                    # We look for qty in column 4 or 5 or 6
                    spec = str(df.iloc[i, 3]).strip()
                    if spec == "nan": spec = ""
                    # SL usually is around col 4, 5, 6. Let's try parsing
                    qty = 0
                    for c_idx in range(4, 9):
                        val = str(df.iloc[i, c_idx]).replace(",", "").strip()
                        if val.replace(".", "", 1).isdigit():
                            qty = float(val)
                            break
                    unit = "cái"
                    
                # Fix unit from material string if possible
                if material.lower() in ['mdf', 'oak', 'gỗ thông']:
                    unit = 'm3'
                
                mat_code = slugify(name + "-" + spec)
                
                data_rows.append((product_id, current_category, mat_code, name, spec, unit, qty))
            except Exception as e:
                pass
                
    c.executemany("INSERT INTO bill_of_materials (product_id, category, material_code, material_name, material_spec, unit, quantity_per_unit) VALUES (?, ?, ?, ?, ?, ?, ?)", data_rows)
    conn.commit()

if __name__ == "__main__":
    import glob
    conn = create_db("database.db")
    # Tự động quét tất cả file excel trong thư mục data/
    files = glob.glob(os.path.join("data", "*.xlsx"))
    
    if len(files) == 0:
        print("Cảnh báo: Không tìm thấy file excel nào trong thư mục 'data/'")
        
    for f in files:
        if not os.path.basename(f).startswith("~$"):
            parse_excel(f, conn)
    
    # Verify
    df_db = pd.read_sql("SELECT * FROM bill_of_materials LIMIT 10", conn)
    print("Sample BOM Data:")
    print(df_db)

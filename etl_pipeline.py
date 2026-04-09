import logging
import pandas as pd
import sqlite3
import unicodedata
import re
import os

# Thiết lập logging để ghi lại các lỗi và thông tin quan trọng trong quá trình ETL
logging.basicConfig(
    filename='etl.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT UNIQUE,
            product_name TEXT
        );
        
        CREATE TABLE IF NOT EXISTS bill_of_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            category TEXT,
            material_code TEXT,
            material_name TEXT,
            material_type TEXT,
            material_spec TEXT,
            technical_desc TEXT,
            unit TEXT,
            quantity_per_unit REAL,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    return conn

def parse_excel(file_obj, conn, default_file_name=None):
    # Determine the display file name
    if default_file_name is None:
        default_file_name = getattr(file_obj, "name", str(file_obj))
    file_name = os.path.basename(default_file_name)
    
    print(f"Parsing {file_name}...")
    logging.info(f"Starting ETL for file: {file_name}")
    df = pd.read_excel(file_obj, sheet_name=0, header=None)
    
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
        product_name = file_name.replace(".xlsx", "").replace(".xls", "")
    
    if product_code == "Unknown" or product_code == "" or product_code == "nan":
        # Lấy file name làm mã, hoặc nếu có dấu '-' (vd: "SKU123 - Tủ gỗ") thì lấy vế trước làm mã
        match = re.match(r"^([a-zA-Z0-9_\s]+)\s*-", product_name)
        if match:
            product_code = match.group(1).strip().upper()
        else:
            # Lấy toàn bộ tên làm mã sản phẩm luôn (bỏ phần đuôi nếu muốn gộp)
            # Hoặc người dùng theo convention đặt tên file là "Tên Mã Sản Phẩm"
            product_code = product_name.upper()

    print(f"Found Product: {product_code} - {product_name}")
    logging.info(f"Extracted product info: {product_code} - {product_name}")
    
    c = conn.cursor()
    # Kiểm tra xem sản phẩm đã có chưa để Upsert đúng chuẩn, không làm mất id
    c.execute("SELECT id FROM products WHERE product_code = ?", (product_code,))
    row = c.fetchone()
    if row:
        product_id = row[0]
        c.execute("UPDATE products SET product_name = ? WHERE id = ?", (product_name, product_id))
        # Clear BOM cũ của sản phẩm này để chạy lại ETL không bị trùng (Upsert/Replace Data)
        c.execute("DELETE FROM bill_of_materials WHERE product_id = ?", (product_id,))
    else:
        c.execute("INSERT INTO products (product_code, product_name) VALUES (?, ?)", (product_code, product_name))
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
                if name == 'nan' or name == '': continue
                
                material = ''
                tech_desc = ''
                unit = ''
                qty = 0
                
                if current_category == 'Nguyên Liệu':
                    material = str(df.iloc[i, 2]).strip()
                    if material == 'nan': material = ''
                    
                    thick = str(df.iloc[i, 3]).strip()
                    width = str(df.iloc[i, 4]).strip()
                    length = str(df.iloc[i, 5]).strip()
                    spec = f"{thick} x {width} x {length}".replace('nan', '0')
                    
                    qty_val = str(df.iloc[i, 6]).strip() if not pd.isna(df.iloc[i, 6]) else ''
                    qty = float(qty_val) if qty_val != '' and qty_val != 'nan' else 0
                    
                    unit = 'm3'
                    if len(df.columns) > 14:
                        td = str(df.iloc[i, 14]).strip()
                        tech_desc = td if td != 'nan' else ''
                        
                elif current_category == 'Vật Tư Lắp Ráp':
                    spec = str(df.iloc[i, 5]).strip()
                    if spec == 'nan': spec = ''
                    
                    for c_idx in range(8, 13):
                        if c_idx < len(df.columns):
                            val = str(df.iloc[i, c_idx]).replace(',', '').strip()
                            if val.replace('.', '', 1).isdigit():
                                qty = float(val)
                                break
                    
                    if len(df.columns) > 12:
                        u = str(df.iloc[i, 12]).strip()
                        unit = u if u != 'nan' else 'cái'
                    else:
                        unit = 'cái'
                        
                    if len(df.columns) > 13:
                        td = str(df.iloc[i, 13]).strip()
                        tech_desc = td if td != 'nan' else ''
                        
                else: # Vật Tư Đóng Gói
                    spec = str(df.iloc[i, 3]).strip()
                    if spec == 'nan': spec = ''
                    
                    for c_idx in range(4, 13):
                        if c_idx < len(df.columns):
                            val = str(df.iloc[i, c_idx]).replace(',', '').strip()
                            if val.replace('.', '', 1).isdigit():
                                qty = float(val)
                                break
                                
                    if len(df.columns) > 8:
                        u = str(df.iloc[i, 8]).strip()
                        unit = u if u != 'nan' else 'cái'
                    else:
                        unit = 'cái'
                        
                    if len(df.columns) > 9:
                        td = str(df.iloc[i, 9]).strip()
                        tech_desc = td if td != 'nan' else ''
                        
                mat_code = slugify(name + '-' + spec + '-' + material + '-' + tech_desc)
                data_rows.append((product_id, current_category, mat_code, name, material, spec, tech_desc, unit, qty))
            except Exception as e:
                print(f"❌ Lỗi dòng {i}: {e}")
                logging.error(f"Parse error at row {i}: {e}")
                
    c.executemany("INSERT INTO bill_of_materials (product_id, category, material_code, material_name, material_type, material_spec, technical_desc, unit, quantity_per_unit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", data_rows)
    conn.commit()
    logging.info(f"Successfully inserted {len(data_rows)} BOM items for product {product_code}")

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

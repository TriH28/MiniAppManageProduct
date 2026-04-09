import re

with open(r'd:\Intern\mini_sale_app\etl_pipeline.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_try_block = r'''            try:
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
            except Exception as e:'''

code = re.sub(r'            try:.*?            except Exception as e:', new_try_block, code, flags=re.DOTALL)

old_insert = 'c.executemany("INSERT INTO bill_of_materials (product_id, category, material_code, material_name, material_spec, unit, quantity_per_unit) VALUES (?, ?, ?, ?, ?, ?, ?)", data_rows)'
new_insert = 'c.executemany("INSERT INTO bill_of_materials (product_id, category, material_code, material_name, material_type, material_spec, technical_desc, unit, quantity_per_unit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", data_rows)'
code = code.replace(old_insert, new_insert)

with open(r'd:\Intern\mini_sale_app\etl_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(code)

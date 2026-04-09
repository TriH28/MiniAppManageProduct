import streamlit as st
import pandas as pd
import sqlite3
import io
import etl_pipeline
import os

DB_PATH = "database.db"

# Đảm bảo DB được tạo sẵn nếu chưa tồn tại
if not os.path.exists(DB_PATH):
    conn = etl_pipeline.create_db(DB_PATH)
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_products():
    conn = get_connection()
    query = "SELECT id, product_code, product_name FROM products"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def load_bom(product_id):
    conn = get_connection()
    query = """
    SELECT 
        category AS `Loại Vật Tư`, 
        material_code AS `Mã Vật Tư`, 
        material_name AS `Tên Chi Tiết`,
        material_type AS `Loại Nguyên Vật Liệu`,
        material_spec AS `Quy cách/Kích thước`,
        technical_desc AS `Mô Tả Kỹ Thuật/Chất Lượng`,
        unit AS `Đơn Vị`, 
        quantity_per_unit AS `Định Mức (1 SP)`
    FROM bill_of_materials 
    WHERE product_id = ?
    ORDER BY category, material_name
    """
    df = pd.read_sql(query, conn, params=(product_id,))
    conn.close()
    return df

st.set_page_config(page_title="BOM Mini-App", layout="wide")

st.title("📦 Quản Lý Cấu Trúc Sản Phẩm (BOM)")
st.markdown("Hệ thống tự động phân tích và tính toán Nhu cầu Vật tư phục vụ sản xuất.")

# Sidebar Controls
st.sidebar.header("Lập Kế Hoạch Sản Xuất")

# --- FILE UPLOAD (Thay thế việc chạy Python tay) ---
st.sidebar.markdown("### 📥 Thêm Sản Phẩm Mới")
uploaded_file = st.sidebar.file_uploader("Kéo thả file Excel (BOM) vào đây", type=["xlsx", "xls"])
if uploaded_file is not None:
    if "last_uploaded" not in st.session_state or st.session_state["last_uploaded"] != uploaded_file.name:
        with st.spinner("Đang phân tích và ghi vào Database..."):
            try:
                conn = etl_pipeline.create_db(DB_PATH)
                etl_pipeline.parse_excel(uploaded_file, conn, default_file_name=uploaded_file.name)
                conn.close()
                st.session_state["last_uploaded"] = uploaded_file.name
                st.sidebar.success(f"Đã lưu thành công: {uploaded_file.name}")
                st.rerun() # Refresh lại dữ liệu ngay lập tức
            except Exception as e:
                st.sidebar.error(f"Lỗi đọc file: {e}")

st.sidebar.markdown("---")

try:
    products_df = load_products()
    if products_df.empty:
        st.info("👋 Chào mừng bạn, hiện hệ thống đang chưa có dữ liệu sản phẩm. Vui lòng upload file Excel ở cột bên trái.")
        st.stop()
        
    # Tạo nhãn hiển thị tránh lặp mã và tên: nếu tên đã chứa/bắt đầu bằng mã hoặc trùng mã, thì chỉ hiện tên.
    labels = []
    for _, row in products_df.iterrows():
        code, name = str(row['product_code']), str(row['product_name'])
        if name.upper().startswith(code.upper()) or code.upper() == name.upper():
            labels.append(name)
        else:
            labels.append(f"{code} - {name}")
            
    products_df['display_label'] = labels
    product_options = products_df['display_label']
    selected_product_str = st.sidebar.selectbox("Chọn Sản Phẩm:", product_options)
    
    # Get ID of selected
    selected_idx = products_df[products_df['display_label'] == selected_product_str].index[0]
    selected_id = int(products_df.loc[selected_idx, 'id'])
    
    production_qty = st.sidebar.number_input("Số lượng:", min_value=1, max_value=10000, value=1)
    if production_qty < 1:
        st.sidebar.error("Số lượng phải ≥ 1")
        st.stop()
    
    st.sidebar.markdown("---")
    
    # Main Body
    st.subheader(f"📊 Bảng Định Mức Vật Tư: {selected_product_str}")
    bom_df = load_bom(selected_id)
    
    if bom_df.empty:
        st.warning("Không tìm thấy dữ liệu cấu trúc vật tư cho sản phẩm này.")
    else:
        # Tự động tính toán số lượng tổng
        # Nhu Cầu = Định Mức * N
        bom_df['Nhu Cầu Mua'] = (bom_df['Định Mức (1 SP)'] * production_qty).round(3)
        
        # Sắp xếp hiển thị
        st.dataframe(bom_df, use_container_width=True, hide_index=True)
        
        # Metrics tổng quan
        st.markdown("### 📈 Tổng quan")
        col1, col2, col3 = st.columns(3)
        col1.metric("Tổng mã vật tư", len(bom_df))
        col2.metric("Số lượng SP yêu cầu", production_qty)
        col3.metric("Tổng nhu cầu mua", bom_df['Nhu Cầu Mua'].sum())
        # Nút Export to Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            bom_df.to_excel(writer, index=False, sheet_name='Nhu Cầu Vật Tư')
            
        st.download_button(
            label="📥 Tải xuống (File Excel) cho Phòng Thu Mua",
            data=buffer.getvalue(),
            file_name=f"NhuCauVatTu_{selected_id}_{production_qty}pcs.xlsx",
            mime="application/vnd.ms-excel",
            type="primary"
        )
except Exception as e:
    st.error(f"Lỗi: {e}")

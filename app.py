import streamlit as st
import pandas as pd
import sqlite3
import io

DB_PATH = "database.db"

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
        material_spec AS `Quy cách/Kích thước`, 
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

try:
    products_df = load_products()
    if products_df.empty:
        st.error("Chưa có dữ liệu sản phẩm trong DB. Hãy chạy etl_pipeline.py trước!")
        st.stop()
        
    product_options = products_df['product_code'] + " - " + products_df['product_name']
    selected_product_str = st.sidebar.selectbox("Chọn Sản Phẩm:", product_options)
    
    # Get ID of selected
    selected_idx = product_options[product_options == selected_product_str].index[0]
    selected_id = int(products_df.loc[selected_idx, 'id'])
    
    production_qty = st.sidebar.number_input("Số lượng cần sản xuất:", min_value=1, value=1, step=1)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Mẹo:** Nếu cần cập nhật dữ liệu, chạy lại module ETL của Data Pipeline.")
    
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

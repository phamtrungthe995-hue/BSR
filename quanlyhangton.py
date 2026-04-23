import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- KẾT NỐI DATABASE ---
conn = sqlite3.connect('inventory_v3.db', check_same_thread=False)
c = conn.cursor()

# Tạo bảng Sản phẩm
c.execute('''CREATE TABLE IF NOT EXISTS products
             (
                 id
                 TEXT
                 PRIMARY
                 KEY,
                 name
                 TEXT,
                 quantity
                 INTEGER
             )''')

# Tạo bảng Lịch sử Giao dịch (Thời gian nhập xuất)
c.execute('''CREATE TABLE IF NOT EXISTS transactions
             (
                 t_id
                 INTEGER
                 PRIMARY
                 KEY
                 AUTOINCREMENT,
                 p_id
                 TEXT,
                 type
                 TEXT,
                 qty
                 INTEGER,
                 timestamp
                 TEXT
             )''')
conn.commit()

st.set_page_config(page_title="Quản lý Kho Thông Minh", layout="wide")
st.title("🚀 Hệ thống Quản lý Kho & Truy xuất Lịch sử")


# --- HÀM HỖ TRỢ ---
def log_transaction(p_id, t_type, qty):
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c.execute("INSERT INTO transactions (p_id, type, qty, timestamp) VALUES (?, ?, ?, ?)",
              (p_id, t_type, qty, now))
    conn.commit()


# --- GIAO DIỆN CHÍNH ---
col1, col2 = st.columns(2)

# --- PHẦN 1: NHẬP KHO ---
with col1:
    with st.expander("➕ Nhập kho / Thêm hàng", expanded=True):
        p_id_input = st.text_input("Nhập Mã sản phẩm (ID)")

        # Kiểm tra xem mã này đã có tên trong DB chưa để gợi ý
        existing_name = ""
        if p_id_input:
            c.execute("SELECT name FROM products WHERE id=?", (p_id_input,))
            res = c.fetchone()
            if res:
                existing_name = res[0]
                st.info(f"Sản phẩm hiện tại: **{existing_name}**")

        p_name = st.text_input("Tên sản phẩm", value=existing_name)
        p_qty = st.number_input("Số lượng nhập", min_value=1, step=1)

        if st.button("Xác nhận Nhập"):
            if p_id_input and p_name:
                c.execute("SELECT quantity FROM products WHERE id=?", (p_id_input,))
                data = c.fetchone()
                if data:
                    new_qty = data[0] + p_qty
                    c.execute("UPDATE products SET quantity=?, name=? WHERE id=?", (new_qty, p_name, p_id_input))
                else:
                    c.execute("INSERT INTO products VALUES (?, ?, ?)", (p_id_input, p_name, p_qty))

                log_transaction(p_id_input, "NHẬP", p_qty)
                st.success(f"Đã nhập {p_qty} {p_name} lúc {datetime.now().strftime('%H:%M:%S')}")
                st.rerun()  # Làm mới lại để cập nhật bảng
            else:
                st.warning("Vui lòng điền đủ Mã và Tên sản phẩm.")

# --- PHẦN 2: XUẤT KHO ---
with col2:
    with st.expander("➖ Xuất kho", expanded=True):
        c.execute("SELECT id FROM products WHERE quantity > 0")
        list_ids = [row[0] for row in c.fetchall()]

        exp_id = st.selectbox("Chọn Mã sản phẩm cần xuất", [""] + list_ids)

        if exp_id:
            # TỰ ĐỘNG HIỂN THỊ TÊN KHI CHỌN MÃ
            c.execute("SELECT name, quantity FROM products WHERE id=?", (exp_id,))
            res = c.fetchone()
            p_name_display = res[0]
            current_stock = res[1]

            st.write(f"Sản phẩm: **{p_name_display}**")
            st.write(f"Tồn kho hiện tại: `{current_stock}`")

            exp_qty = st.number_input("Số lượng xuất", min_value=1, max_value=current_stock, step=1)

            if st.button("Xác nhận Xuất"):
                new_qty = current_stock - exp_qty
                c.execute("UPDATE products SET quantity=? WHERE id=?", (new_qty, exp_id))

                log_transaction(exp_id, "XUẤT", exp_qty)
                st.success(f"Đã xuất {exp_qty} {p_name_display}")
                st.rerun()

st.divider()

# --- PHẦN 3: HIỂN THỊ DỮ LIỆU ---
tab1, tab2 = st.tabs(["📊 Tồn kho hiện tại", "📜 Lịch sử Nhập/Xuất"])

with tab1:
    df_stock = pd.read_sql_query("SELECT id as 'Mã SP', name as 'Tên SP', quantity as 'Số lượng' FROM products", conn)
    st.dataframe(df_stock, use_container_width=True)

with tab2:
    df_history = pd.read_sql_query("""
                                   SELECT t.timestamp as 'Thời gian', t.p_id as 'Mã SP', p.name as 'Tên SP', t.type as 'Loại giao dịch', t.qty as 'Số lượng'
                                   FROM transactions t
                                            JOIN products p ON t.p_id = p.id
                                   ORDER BY t.t_id DESC
                                   """, conn)
    st.dataframe(df_history, use_container_width=True)
  streamlit
pandas

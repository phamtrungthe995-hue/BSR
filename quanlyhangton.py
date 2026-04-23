import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BSR shop - Quản lý kho & Giá", layout="wide", page_icon="🛍️")


# --- HÀM KIỂM TRA ĐĂNG NHẬP ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Đăng nhập BSR shop")
        user = st.text_input("Tên đăng nhập")
        pw = st.text_input("Mật khẩu", type="password")
        if st.button("Đăng nhập"):
            if user == "admin" and pw == "bsr123":  # Bạn có thể đổi mật khẩu tại đây
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Sai tài khoản hoặc mật khẩu")
        return False
    return True


# --- CHƯƠNG TRÌNH CHÍNH ---
if check_password():
    # Kết nối Database
    conn = sqlite3.connect('bsr_inventory_v2.db', check_same_thread=False)
    c = conn.cursor()

    # Cập nhật bảng products: Thêm cột giá nhập và giá bán
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (
                     id
                     TEXT
                     PRIMARY
                     KEY,
                     name
                     TEXT,
                     quantity
                     INTEGER,
                     import_price
                     REAL,
                     selling_price
                     REAL
                 )''')

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

    # Sidebar
    st.sidebar.title("Cài đặt")
    if st.sidebar.button("Đăng xuất"):
        del st.session_state["password_correct"]
        st.rerun()

    st.title("🛍️ BSR shop - Hệ thống Quản lý Kho & Tài chính")

    col1, col2 = st.columns(2)

    # --- PHẦN NHẬP KHO ---
    with col1:
        with st.expander("➕ Nhập kho / Thêm hàng", expanded=True):
            p_id = st.text_input("Mã sản phẩm (ID)")

            # Khởi tạo giá trị mặc định
            p_name_val = ""
            p_import_val = 0.0
            p_selling_val = 0.0

            if p_id:
                c.execute("SELECT name, import_price, selling_price FROM products WHERE id=?", (p_id.strip(),))
                res = c.fetchone()
                if res:
                    p_name_val, p_import_val, p_selling_val = res
                    st.info(f"Sản phẩm: **{p_name_val}** | Giá nhập cũ: {p_import_val:,.0f}đ")

            p_name = st.text_input("Tên sản phẩm", value=p_name_val)

            c_price1, c_price2 = st.columns(2)
            with c_price1:
                p_import = st.number_input("Giá nhập (VNĐ)", min_value=0.0, value=float(p_import_val), step=1000.0)
            with c_price2:
                p_selling = st.number_input("Giá bán (VNĐ)", min_value=0.0, value=float(p_selling_val), step=1000.0)

            p_qty = st.number_input("Số lượng nhập thêm", min_value=1, step=1)

            if st.button("Xác nhận Nhập hàng"):
                if p_id and p_name:
                    c.execute("SELECT quantity FROM products WHERE id=?", (p_id.strip(),))
                    data = c.fetchone()
                    if data:
                        new_qty = data[0] + p_qty
                        c.execute("UPDATE products SET quantity=?, name=?, import_price=?, selling_price=? WHERE id=?",
                                  (new_qty, p_name, p_import, p_selling, p_id.strip()))
                    else:
                        c.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?)",
                                  (p_id.strip(), p_name, p_qty, p_import, p_selling))

                    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    c.execute("INSERT INTO transactions (p_id, type, qty, timestamp) VALUES (?, 'NHẬP', ?, ?)",
                              (p_id.strip(), p_qty, now))
                    conn.commit()
                    st.success("Đã cập nhật kho và giá!")
                    st.rerun()

    # --- PHẦN XUẤT KHO ---
    with col2:
        with st.expander("➖ Xuất kho", expanded=True):
            c.execute("SELECT id FROM products WHERE quantity > 0")
            ids = [r[0] for r in c.fetchall()]
            exp_id = st.selectbox("Chọn Mã SP cần xuất", [""] + ids)

            if exp_id:
                c.execute("SELECT name, quantity, selling_price FROM products WHERE id=?", (exp_id,))
                res = c.fetchone()
                st.warning(f"Sản phẩm: {res[0]} | Tồn: {res[1]} | Giá bán: {res[2]:,.0f}đ")
                exp_qty = st.number_input("Số lượng xuất", min_value=1, max_value=res[1], step=1)

                if st.button("Xác nhận Xuất"):
                    c.execute("UPDATE products SET quantity=? WHERE id=?", (res[1] - exp_qty, exp_id))
                    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    c.execute("INSERT INTO transactions (p_id, type, qty, timestamp) VALUES (?, 'XUẤT', ?, ?)",
                              (exp_id, exp_qty, now))
                    conn.commit()
                    st.rerun()

    st.divider()

    # --- BÁO CÁO & THỐNG KÊ ---
    tab1, tab2 = st.tabs(["📊 Tình trạng kho", "📜 Nhật ký giao dịch"])

    with tab1:
        df = pd.read_sql_query("""
                               SELECT id as 'Mã SP', name as 'Tên SP', quantity as 'Tồn kho', import_price as 'Giá nhập', selling_price as 'Giá bán'
                               FROM products
                               """, conn)

        # Tính toán giá trị kho
        df['Tổng vốn'] = df['Tồn kho'] * df['Giá nhập']

        st.dataframe(df.style.format({
            'Giá nhập': '{:,.0f}đ',
            'Giá bán': '{:,.0f}đ',
            'Tổng vốn': '{:,.0f}đ'
        }), use_container_width=True)

        # Hiển thị tổng vốn lưu động
        total_value = df['Tổng vốn'].sum()
        st.metric("Tổng giá trị hàng tồn (Vốn)", f"{total_value:,.0f} VNĐ")

    with tab2:
        df_h = pd.read_sql_query("""
                                 SELECT t.timestamp as 'Thời gian', t.p_id as 'Mã SP', p.name as 'Tên SP', t.type as 'Giao dịch', t.qty as 'Số lượng'
                                 FROM transactions t
                                          JOIN products p ON t.p_id = p.id
                                 ORDER BY t.t_id DESC
                                 """, conn)
        st.dataframe(df_h, use_container_width=True)

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
streamlit
pandas
# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BSR shop - Quản lý kho", layout="wide", page_icon="🛍️")


# --- HÀM KIỂM TRA ĐĂNG NHẬP ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Đăng nhập BSR shop")
        user = st.text_input("Tên đăng nhập")
        pw = st.text_input("Mật khẩu", type="password")
        if st.button("Đăng nhập"):
            if user == "admin" and pw == "bsr123":  # Bạn có thể đổi pass ở đây
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Sai tài khoản hoặc mật khẩu")
        return False
    return True


# --- CHƯƠNG TRÌNH CHÍNH ---
if check_password():
    # Kết nối Database (Sẽ tự tạo file .db trên server khi deploy)
    conn = sqlite3.connect('bsr_inventory.db', check_same_thread=False)
    c = conn.cursor()
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

    st.sidebar.title("Cài đặt")
    if st.sidebar.button("Đăng xuất"):
        del st.session_state["password_correct"]
        st.rerun()

    st.title("🛍️ BSR shop - Hệ thống Quản lý Kho")

    col1, col2 = st.columns(2)

    with col1:
        with st.expander("➕ Nhập kho / Thêm hàng", expanded=True):
            p_id = st.text_input("Mã sản phẩm (ID)")
            p_name_val = ""
            if p_id:
                c.execute("SELECT name FROM products WHERE id=?", (p_id.strip(),))
                res = c.fetchone()
                if res: p_name_val = res[0]

            p_name = st.text_input("Tên sản phẩm", value=p_name_val)
            p_qty = st.number_input("Số lượng nhập", min_value=1, step=1)

            if st.button("Xác nhận Nhập"):
                if p_id and p_name:
                    c.execute("SELECT quantity FROM products WHERE id=?", (p_id.strip(),))
                    data = c.fetchone()
                    if data:
                        c.execute("UPDATE products SET quantity=?, name=? WHERE id=?",
                                  (data[0] + p_qty, p_name, p_id.strip()))
                    else:
                        c.execute("INSERT INTO products VALUES (?, ?, ?)", (p_id.strip(), p_name, p_qty))

                    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    c.execute("INSERT INTO transactions (p_id, type, qty, timestamp) VALUES (?, 'NHẬP', ?, ?)",
                              (p_id.strip(), p_qty, now))
                    conn.commit()
                    st.success("Đã cập nhật kho!")
                    st.rerun()

    with col2:
        with st.expander("➖ Xuất kho", expanded=True):
            c.execute("SELECT id FROM products WHERE quantity > 0")
            ids = [r[0] for r in c.fetchall()]
            exp_id = st.selectbox("Chọn Mã SP", [""] + ids)
            if exp_id:
                c.execute("SELECT name, quantity FROM products WHERE id=?", (exp_id,))
                res = c.fetchone()
                st.info(f"Sản phẩm: {res[0]} | Tồn: {res[1]}")
                exp_qty = st.number_input("Số lượng xuất", min_value=1, max_value=res[1], step=1)
                if st.button("Xác nhận Xuất"):
                    c.execute("UPDATE products SET quantity=? WHERE id=?", (res[1] - exp_qty, exp_id))
                    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    c.execute("INSERT INTO transactions (p_id, type, qty, timestamp) VALUES (?, 'XUẤT', ?, ?)",
                              (exp_id, exp_qty, now))
                    conn.commit()
                    st.rerun()

    st.divider()
    tab1, tab2 = st.tabs(["📊 Tồn kho", "📜 Lịch sử"])
    with tab1:
        df = pd.read_sql_query("SELECT id, name, quantity FROM products", conn)
        st.dataframe(df, use_container_width=True)
    with tab2:
        df_h = pd.read_sql_query("SELECT timestamp, p_id, type, qty FROM transactions ORDER BY t_id DESC", conn)
        st.dataframe(df_h, use_container_width=True)

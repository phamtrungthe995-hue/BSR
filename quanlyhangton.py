import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BSR shop - Quản lý kho", layout="wide", page_icon="🛍️")


# --- HÀM KIỂM TRA ĐĂNG NHẬP ---
def check_password():
    """Trả về True nếu người dùng nhập đúng mật khẩu."""

    def password_entered():
        """Kiểm tra mật khẩu người dùng nhập vào."""
        if (
                st.session_state["username"] == "admin"
                and st.session_state["password"] == "bsr123"
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Xóa password khỏi session để bảo mật
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Hiển thị form đăng nhập lần đầu
        st.title("🔐 Đăng nhập BSR shop")
        st.text_input("Tên đăng nhập", key="username")
        st.text_input("Mật khẩu", type="password", key="password")
        st.button("Đăng nhập", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        # Nếu nhập sai
        st.title("🔐 Đăng nhập BSR shop")
        st.text_input("Tên đăng nhập", key="username")
        st.text_input("Mật khẩu", type="password", key="password")
        st.button("Đăng nhập", on_click=password_entered)
        st.error("😕 Sai tên đăng nhập hoặc mật khẩu")
        return False
    else:
        # Mật khẩu đúng
        return True


# --- CHƯƠNG TRÌNH CHÍNH ---
if check_password():
    # Chỉ khi đăng nhập đúng mới chạy phần code quản lý kho bên dưới

    # Kết nối Database
    conn = sqlite3.connect('bsr_shop_inventory.db', check_same_thread=False)
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


    def log_transaction(p_id, t_type, qty):
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        c.execute("INSERT INTO transactions (p_id, type, qty, timestamp) VALUES (?, ?, ?, ?)", (p_id, t_type, qty, now))
        conn.commit()


    # Nút đăng xuất
    if st.sidebar.button("Đăng xuất"):
        del st.session_state["password_correct"]
        st.rerun()

    st.title("🛍️ BSR shop - Hệ thống Quản lý Kho")

    col1, col2 = st.columns(2)

    with col1:
        with st.expander("➕ Nhập kho / Thêm hàng", expanded=True):
            p_id_input = st.text_input("Nhập Mã sản phẩm (ID)")
            existing_name = ""
            if p_id_input:
                c.execute("SELECT name FROM products WHERE id=?", (p_id_input.strip(),))
                res = c.fetchone()
                if res: existing_name = res[0]

            p_name = st.text_input("Tên sản phẩm", value=existing_name)
            p_qty = st.number_input("Số lượng nhập", min_value=1, step=1)

            if st.button("Xác nhận Nhập hàng"):
                if p_id_input and p_name:
                    c.execute("SELECT quantity FROM products WHERE id=?", (p_id_input.strip(),))
                    data = c.fetchone()
                    if data:
                        new_qty = data[0] + p_qty
                        c.execute("UPDATE products SET quantity=?, name=? WHERE id=?",
                                  (new_qty, p_name, p_id_input.strip()))
                    else:
                        c.execute("INSERT INTO products VALUES (?, ?, ?)", (p_id_input.strip(), p_name, p_qty))
                    log_transaction(p_id_input.strip(), "NHẬP", p_qty)
                    st.success("Đã cập nhật kho!")
                    st.rerun()

    with col2:
        with st.expander("➖ Xuất kho", expanded=True):
            c.execute("SELECT id FROM products WHERE quantity > 0")
            list_ids = [row[0] for row in c.fetchall()]
            exp_id = st.selectbox("Chọn Mã sản phẩm", [""] + list_ids)
            if exp_id:
                c.execute("SELECT name, quantity FROM products WHERE id=?", (exp_id,))
                res = c.fetchone()
                st.write(f"Sản phẩm: **{res[0]}** | Tồn: `{res[1]}`")
                exp_qty = st.number_input("Số lượng xuất", min_value=1, max_value=res[1], step=1)
                if st.button("Xác nhận Xuất hàng"):
                    c.execute("UPDATE products SET quantity=? WHERE id=?", (res[1] - exp_qty, exp_id))
                    log_transaction(exp_id, "XUẤT", exp_qty)
                    st.success("Đã xuất hàng!")
                    st.rerun()

    st.divider()
    tab1, tab2 = st.tabs(["📊 Báo cáo Tồn kho", "📜 Nhật ký Nhập/Xuất"])

    with tab1:
        df_stock = pd.read_sql_query("SELECT id as 'Mã SP', name as 'Tên SP', quantity as 'Số lượng tồn' FROM products",
                                     conn)
        st.dataframe(df_stock, use_container_width=True, hide_index=True)

    with tab2:
        df_history = pd.read_sql_query(
            "SELECT t.timestamp as 'Thời gian', t.p_id as 'Mã SP', p.name as 'Tên SP', t.type as 'Giao dịch', t.qty as 'Số lượng' FROM transactions t JOIN products p ON t.p_id = p.id ORDER BY t.t_id DESC",
            conn)
        st.dataframe(df_history, use_container_width=True, hide_index=True)


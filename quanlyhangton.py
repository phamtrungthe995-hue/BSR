import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BSR shop - Quản lý Kho & Vốn", layout="wide", page_icon="💰")

# --- HÀM KIỂM TRA ĐĂNG NHẬP ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Đăng nhập BSR shop")
        user = st.text_input("Tên đăng nhập")
        pw = st.text_input("Mật khẩu", type="password")
        if st.button("Đăng nhập"):
            if user == "admin" and pw == "bsr123":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Sai tài khoản hoặc mật khẩu")
        return False
    return True

# --- CHƯƠNG TRÌNH CHÍNH ---
if check_password():
    # Kết nối Database
    conn = sqlite3.connect('bsr_inventory_v5.db', check_same_thread=False)
    c = conn.cursor()

    # Bảng sản phẩm
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id TEXT PRIMARY KEY, name TEXT, quantity INTEGER, 
                  import_price REAL, selling_price REAL)''')

    # Bảng giao dịch
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (t_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  p_id TEXT,type TEXT,qty INTEGER,
                  unit_price REAL,total_val REAL,timestamp TEXT)''')
    conn.commit()

    # Sidebar
    st.sidebar.title("BSR shop Admin")
    if st.sidebar.button("Đăng xuất"):
        del st.session_state["password_correct"]
        st.rerun()

    st.title("🏪 BSR shop - Quản lý Kho & Giá trị Vốn")

    col1, col2 = st.columns(2)

    # --- PHẦN NHẬP KHO ---
    with col1:
        with st.expander("➕ Nhập kho", expanded=True):
            p_id = st.text_input("Mã sản phẩm (ID)")
            p_name_val, p_import_val, p_selling_val = "", 0.0, 0.0
            if p_id:
                c.execute("SELECT name, import_price, selling_price FROM products WHERE id=?", (p_id.strip(),))
                res = c.fetchone()
                if res: p_name_val, p_import_val, p_selling_val = res

            p_name = st.text_input("Tên sản phẩm", value=p_name_val)
            p_import = st.number_input("Giá nhập (VNĐ)", min_value=0.0, value=float(p_import_val))
            p_selling = st.number_input("Giá bán (VNĐ)", min_value=0.0, value=float(p_selling_val))
            p_qty = st.number_input("Số lượng nhập", min_value=1, step=1)

            if st.button("Xác nhận Nhập"):
                if p_id and p_name:
                    c.execute("SELECT quantity FROM products WHERE id=?", (p_id.strip(),))
                    data = c.fetchone()
                    new_qty = (data[0] + p_qty) if data else p_qty

                    if data:
                        c.execute("UPDATE products SET quantity=?, name=?, import_price=?, selling_price=? WHERE id=?",
                                  (new_qty, p_name, p_import, p_selling, p_id.strip()))
                    else:
                        c.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?)", (p_id.strip(), p_name, p_qty, p_import, p_selling))

                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO transactions (p_id, type, qty, unit_price, total_val, timestamp) VALUES (?, 'NHẬP', ?, ?, ?, ?)",
                              (p_id.strip(), p_qty, p_import, p_qty * p_import, now))
                    conn.commit()
                    st.success("Đã nhập hàng!")
                    st.rerun()

    # --- PHẦN XUẤT KHO ---
    with col2:
        with st.expander("➖ Xuất kho", expanded=True):
            c.execute("SELECT id FROM products WHERE quantity > 0")
            ids = [r[0] for r in c.fetchall()]
            exp_id = st.selectbox("Chọn Mã SP", [""] + ids)
            if exp_id:
                c.execute("SELECT name, quantity, selling_price FROM products WHERE id=?", (exp_id,))
                res = c.fetchone()
                st.info(f"Sản phẩm: {res[0]} | Tồn: {res[1]}")
                exp_qty = st.number_input("Số lượng xuất", min_value=1, max_value=res[1], step=1)
                if st.button("Xác nhận Xuất"):
                    c.execute("UPDATE products SET quantity=? WHERE id=?", (res[1] - exp_qty, exp_id))
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO transactions (p_id, type, qty, unit_price, total_val, timestamp) VALUES (?, 'XUẤT', ?, ?, ?, ?)",
                              (exp_id, exp_qty, res[2], exp_qty * res[2], now))
                    conn.commit()
                    st.rerun()

    st.divider()

    # --- HỆ THỐNG BÁO CÁO ---
    tab1, tab2, tab3 = st.tabs(["📊 Tồn kho & Vốn tồn", "📜 Nhật ký", "💰 Báo cáo Tháng"])

    with tab1:
        st.subheader("Chi tiết hàng tồn và Giá trị vốn")
        df_stock = pd.read_sql_query("SELECT id as 'Mã SP', name as 'Tên SP', quantity as 'Số lượng', import_price as 'Giá nhập', selling_price as 'Giá bán' FROM products", conn)

        if not df_stock.empty:
            # Tính tổng vốn cho từng mặt hàng
            df_stock['Vốn tồn kho'] = df_stock['Số lượng'] * df_stock['Giá nhập']

            # Hiển thị bảng với định dạng tiền tệ
            st.dataframe(df_stock.style.format({
                'Giá nhập': '{:,.0f}đ',
                'Giá bán': '{:,.0f}đ',
                'Vốn tồn kho': '{:,.0f}đ'
            }), use_container_width=True)

            # Hiển thị Tổng vốn tổng cộng
            total_stock_value = df_stock['Vốn tồn kho'].sum()
            st.metric("TỔNG GIÁ TRỊ VỐN TỒN KHO HIỆN TẠI", f"{total_stock_value:,.0f} VNĐ")
        else:
            st.info("Kho hàng đang trống.")

    with tab2:
        df_h = pd.read_sql_query("SELECT timestamp as 'Thời gian', p_id as 'Mã SP', type as 'Giao dịch', qty as 'SL', total_val as 'Tổng tiền' FROM transactions ORDER BY t_id DESC", conn)
        st.dataframe(df_h.style.format({'Tổng tiền': '{:,.0f}đ'}), use_container_width=True)

    with tab3:
        st.subheader("Tổng giá trị Nhập/Xuất theo tháng")
        df_trans = pd.read_sql_query("SELECT type, total_val, timestamp FROM transactions", conn)

        if not df_trans.empty:
            df_trans['timestamp'] = pd.to_datetime(df_trans['timestamp'])
            df_trans['Tháng'] = df_trans['timestamp'].dt.strftime('%m/%Y')
            report = df_trans.groupby(['Tháng', 'type'])['total_val'].sum().unstack(fill_value=0)

            if 'NHẬP' not in report.columns: report['NHẬP'] = 0
            if 'XUẤT' not in report.columns: report['XUẤT'] = 0

            report = report.rename(columns={'NHẬP': 'Tiền nhập hàng', 'XUẤT': 'Tiền bán hàng'})
            report['Chênh lệch thu-chi'] = report['Tiền bán hàng'] - report['Tiền nhập hàng']

            st.table(report.style.format("{:,.0f}đ"))
        else:
            st.info("Chưa có giao dịch.")

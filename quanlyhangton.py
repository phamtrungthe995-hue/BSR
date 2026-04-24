import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BSR Shop Pro", layout="wide", page_icon="💰")

# --- KẾT NỐI DATABASE ---
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('bsr_inventory_v5.db', check_same_thread=False)
    return conn

conn = get_connection()
c = conn.cursor()

# Khởi tạo các bảng
c.execute('''CREATE TABLE IF NOT EXISTS products
             (id TEXT PRIMARY KEY, name TEXT, quantity INTEGER, 
              import_price REAL, selling_price REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS transactions
             (t_id INTEGER PRIMARY KEY AUTOINCREMENT,
              p_id TEXT,type TEXT,qty INTEGER,
              unit_price REAL,total_val REAL,profit REAL,timestamp TEXT)''')

# Tự động cập nhật cột 'profit' nếu database cũ chưa có
try:
    c.execute("ALTER TABLE transactions ADD COLUMN profit REAL DEFAULT 0")
    conn.commit()
except sqlite3.OperationalError:
    pass

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
    st.sidebar.title("🚀 BSR Shop Admin")
    menu = st.sidebar.radio("Menu quản lý", ["Giao dịch & Kho", "Quản lý Danh mục", "Báo cáo Tài chính"])

    if st.sidebar.button("Đăng xuất"):
        del st.session_state["password_correct"]
        st.rerun()

    # --- TAB 1: NHẬP & XUẤT ---
    if menu == "Giao dịch & Kho":
        st.title("🏪 Nhập hàng & Bán hàng")
        col1, col2 = st.columns(2)

        with col1:
            with st.expander("➕ Nhập kho (Hàng về)", expanded=True):
                p_id = st.text_input("Mã sản phẩm (ID)")
                p_name_val, p_imp_val, p_sel_val = "", 0.0, 0.0
                if p_id:
                    c.execute("SELECT name, import_price, selling_price FROM products WHERE id=?", (p_id.strip(),))
                    res = c.fetchone()
                    if res: p_name_val, p_imp_val, p_sel_val = res

                p_name = st.text_input("Tên sản phẩm", value=p_name_val)
                p_import = st.number_input("Giá nhập (VNĐ)", min_value=0.0, value=float(p_imp_val), step=1000.0)
                p_selling = st.number_input("Giá bán (VNĐ)", min_value=0.0, value=float(p_sel_val), step=1000.0)
                p_qty = st.number_input("Số lượng nhập thêm", min_value=1, step=1)

                if st.button("Xác nhận NHẬP"):
                    c.execute("SELECT quantity FROM products WHERE id=?", (p_id.strip(),))
                    data = c.fetchone()
                    new_qty = (data[0] + p_qty) if data else p_qty
                    c.execute("INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?, ?)", (p_id.strip(), p_name, new_qty, p_import, p_selling))
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO transactions (p_id, type, qty, unit_price, total_val, profit, timestamp) VALUES (?, 'NHẬP', ?, ?, ?, 0, ?)",
                              (p_id.strip(), p_qty, p_import, p_qty * p_import, now))
                    conn.commit()
                    st.success("Đã cập nhật kho!")
                    st.rerun()

        with col2:
            with st.expander("➖ Xuất kho (Bán lẻ)", expanded=True):
                c.execute("SELECT id, name, quantity, selling_price, import_price FROM products WHERE quantity > 0")
                stock_data = c.fetchall()
                options = {f"{r[0]} - {r[1]} (Tồn: {r[2]})": r for r in stock_data}
                sel_label = st.selectbox("Chọn sản phẩm bán", [""] + list(options.keys()))

                if sel_label:
                    p_info = options[sel_label]
                    e_id, e_name, e_stock, e_sell, e_imp = p_info
                    e_qty = st.number_input("Số lượng bán", min_value=1, max_value=e_stock, step=1)
                    total_sell = e_qty * e_sell
                    profit = e_qty * (e_sell - e_imp) # Lợi nhuận = (Giá bán - Giá nhập) * SL

                    st.warning(f"Thành tiền: {total_sell:,.0f}đ")
                    if st.button("Xác nhận BÁN"):
                        c.execute("UPDATE products SET quantity=? WHERE id=?", (e_stock - e_qty, e_id))
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        c.execute("INSERT INTO transactions (p_id, type, qty, unit_price, total_val, profit, timestamp) VALUES (?, 'XUẤT', ?, ?, ?, ?, ?)",
                                  (e_id, e_qty, e_sell, total_sell, profit, now))
                        conn.commit()
                        st.balloons()
                        st.rerun()

    # --- TAB 2: QUẢN LÝ DANH MỤC & ĐIỀU CHỈNH SAI SÓT ---
    elif menu == "Quản lý Danh mục":
        st.title("📦 Quản lý tồn kho & Điều chỉnh")
        df_stock = pd.read_sql_query("SELECT id, name, quantity, import_price, selling_price FROM products", conn)

        if not df_stock.empty:
            df_stock['Giá trị vốn tồn'] = df_stock['quantity'] * df_stock['import_price']

            # Chỉ số tổng quan
            m1, m2 = st.columns(2)
            m1.metric("TỔNG GIÁ TRỊ VỐN TỒN KHO", f"{df_stock['Giá trị vốn tồn'].sum():,.0f} VNĐ")
            m2.metric("TỔNG SỐ LƯỢNG HÀNG", f"{df_stock['quantity'].sum():,.0f} SP")

            st.dataframe(df_stock.style.format({'import_price': '{:,.0f}', 'selling_price': '{:,.0f}', 'Giá trị vốn tồn': '{:,.0f}'}), use_container_width=True)

            st.divider()
            # Tính năng sửa sai
            st.subheader("🛠️ Sửa lỗi nhập sai số liệu")
            adj_id = st.selectbox("Chọn Mã SP cần điều chỉnh", [""] + df_stock['id'].tolist())
            if adj_id:
                row = df_stock[df_stock['id'] == adj_id].iloc[0]
                st.info(f"Sản phẩm: {row['name']} | Đang tồn: {row['quantity']}")
                new_actual_qty = st.number_input("Nhập số lượng thực tế chính xác", min_value=0, step=1, value=int(row['quantity']))

                if st.button("Cập nhật số thực tế"):
                    diff = new_actual_qty - row['quantity']
                    c.execute("UPDATE products SET quantity=? WHERE id=?", (new_actual_qty, adj_id))
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # Ghi loại 'ĐIỀU CHỈNH' để không nhầm với Nhập hàng/Bán hàng
                    c.execute("INSERT INTO transactions (p_id, type, qty, unit_price, total_val, profit, timestamp) VALUES (?, 'ĐIỀU CHỈNH', ?, 0, 0, 0, ?)",
                              (adj_id, diff, now))
                    conn.commit()
                    st.success("Đã điều chỉnh kho!")
                    st.rerun()
        else:
            st.info("Chưa có sản phẩm nào.")

    # --- TAB 3: BÁO CÁO TÀI CHÍNH ---
    elif menu == "Báo cáo Tài chính":
        st.title("📈 Phân tích Doanh thu & Vốn")

        # Lấy dữ liệu sản phẩm để tính vốn tồn hiện tại
        df_products = pd.read_sql_query("SELECT quantity, import_price FROM products", conn)
        current_capital_value = (df_products['quantity'] * df_products['import_price']).sum()

        st.metric("GIÁ TRỊ VỐN TRONG KHO HIỆN TẠI", f"{current_capital_value:,.0f} VNĐ")

        # Lấy dữ liệu giao dịch
        df_trans = pd.read_sql_query("SELECT * FROM transactions", conn)
        if not df_trans.empty:
            df_trans['timestamp'] = pd.to_datetime(df_trans['timestamp'], errors='coerce')
            df_trans['Tháng'] = df_trans['timestamp'].dt.strftime('%m/%Y')

            # Lọc riêng các giao dịch Bán hàng (XUẤT)
            sales = df_trans[df_trans['type'] == 'XUẤT']
            if not sales.empty:
                monthly_report = sales.groupby('Tháng').agg({
                    'total_val': 'sum',
                    'profit': 'sum'
                }).rename(columns={'total_val': 'Doanh thu', 'profit': 'Lợi nhuận gộp'})

                st.subheader("Báo cáo Doanh thu & Lợi nhuận theo tháng")
                st.table(monthly_report.style.format("{:,.0f}đ"))
                st.bar_chart(monthly_report)
            else:
                st.info("Chưa có dữ liệu bán hàng để lập báo cáo doanh thu.")

            with st.expander("Xem nhật ký giao dịch chi tiết"):
                st.dataframe(df_trans.sort_values('t_id', ascending=False), use_container_width=True)
        else:
            st.info("Chưa có giao dịch phát sinh.")

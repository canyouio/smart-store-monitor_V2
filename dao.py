import pymysql
import pandas as pd
import random
from datetime import datetime
from config import DB_CONFIG

def get_connection():
    return pymysql.connect(
        host=DB_CONFIG['host'], port=DB_CONFIG['port'],
        user=DB_CONFIG['user'], password=DB_CONFIG['password'],
        database=DB_CONFIG['database'], charset=DB_CONFIG['charset'],
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY, category VARCHAR(50) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS visits (
                id INT AUTO_INCREMENT PRIMARY KEY, action VARCHAR(20) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL)''')
            
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE username='admin'")
            if cursor.fetchone()['count'] == 0:
                cursor.execute("INSERT INTO users (username, password) VALUES ('admin', '123456')")
                
            cursor.execute("SELECT COUNT(*) as count FROM orders")
            if cursor.fetchone()['count'] <= 5:
                categories = ['鲜食便当', '碳酸饮料', '休闲零食', '乳制品', '日用百货']
                for _ in range(300):
                    cat = random.choice(categories)
                    amt = round(random.uniform(5.0, 35.0), 2)
                    cursor.execute("INSERT INTO orders (category, amount) VALUES (%s, %s)", (cat, amt))
        conn.commit()
    finally:
        conn.close()

def get_filtered_orders(category=None, min_amount=None, max_amount=None, page=1, per_page=10):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql_filter = "FROM orders WHERE 1=1"
            params = []
            if category:
                sql_filter += " AND category = %s"
                params.append(category)
            if min_amount is not None:
                sql_filter += " AND amount >= %s"
                params.append(min_amount)
            if max_amount is not None:
                sql_filter += " AND amount <= %s"
                params.append(max_amount)

            # 查询总数
            cursor.execute("SELECT COUNT(*) as total " + sql_filter, params)
            total = cursor.fetchone()['total']

            # 分页查询数据
            offset = (page - 1) * per_page
            cursor.execute(f"SELECT * {sql_filter} ORDER BY timestamp DESC LIMIT %s OFFSET %s", params + [per_page, offset])
            records = cursor.fetchall()

            # 💡 关键：处理时间对象，将其转为字符串，否则 jsonify 会报错
            for r in records:
                if 'timestamp' in r and r['timestamp']:
                    r['timestamp'] = r['timestamp'].strftime("%Y-%m-%d %H:%M:%S")

            return records, total
    finally:
        conn.close()

def get_all_orders_df():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM orders")
            return pd.DataFrame(cursor.fetchall())
    finally: conn.close()

def get_total_revenue():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT SUM(amount) as total FROM orders")
            res = cursor.fetchone()
            return float(res['total']) if res and res['total'] else 0.0
    finally: conn.close()

def insert_order(cat, amt):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO orders (category, amount) VALUES (%s, %s)", (cat, amt))
        conn.commit()
    finally: conn.close()

def update_order(oid, cat, amt):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE orders SET category=%s, amount=%s WHERE id=%s", (cat, amt, oid))
        conn.commit()
    finally: conn.close()

def delete_order(oid):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM orders WHERE id=%s", (oid,))
        conn.commit()
    finally: conn.close()

def insert_visit(action):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO visits (action) VALUES (%s)", (action,))
        conn.commit()
    finally: conn.close()

def verify_user(u, p):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (u, p))
            return cursor.fetchone() is not None
    finally: conn.close()
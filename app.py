import time
import random
import threading
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from flask_socketio import SocketIO

# 导入 dao.py 中我们刚刚更新的方法
from dao import (init_db, insert_order, insert_visit, verify_user, 
                 get_filtered_orders, delete_order, update_order)
from service import AnalyticsService, RealtimeService

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart_store_secure_key_2026'
app.config['TEMPLATES_AUTO_RELOAD'] = True 
socketio = SocketIO(app, cors_allowed_origins="*")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- 后台模拟传感器线程 ---
def background_sensor_simulator():
    categories = ['鲜食便当', '碳酸饮料', '休闲零食', '乳制品', '日用百货']
    while True:
        time.sleep(2.5)
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        
        change = random.choice([-1, 0, 1, 1]) 
        action = 'enter' if change > 0 else ('exit' if change < 0 else 'none')
        
        if action != 'none':
            insert_visit(action)
            if action == 'exit' and random.random() > 0.6:
                cat = random.choice(categories)
                amount = round(random.uniform(5.0, 50.0), 2)
                insert_order(cat, amount)
            RealtimeService.process_sensor_event(action)

        RealtimeService.sync_revenue_from_db()
        state = RealtimeService.get_current_state()
        RealtimeService.append_to_queue(time_str, state['current_inside'])
        
        socketio.emit('store_update', {
            'time': time_str,
            'current_inside': state['current_inside'],
            'revenue': state['revenue'],
            'visitors': state['visitors']
        })

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if verify_user(username, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误！', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session.get('username'))

# 💡 Vue 页面入口：只负责返回 HTML 壳子
@app.route('/manage')
@login_required
def manage():
    return render_template('manage.html', username=session.get('username'))

# 💡 核心：专门为 Vue 提供数据的 JSON 接口
@app.route('/api/orders', methods=['GET'])
@login_required
def api_get_orders():
    category = request.args.get('category', '').strip()
    try:
        min_amount = float(request.args.get('min_amount')) if request.args.get('min_amount') else None
    except: min_amount = None
    try:
        max_amount = float(request.args.get('max_amount')) if request.args.get('max_amount') else None
    except: max_amount = None
    
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # 调用 dao.py 中的过滤查询
    orders, total_records = get_filtered_orders(
        category=category if category else None,
        min_amount=min_amount,
        max_amount=max_amount,
        page=page,
        per_page=per_page
    )
    
    return jsonify({
        "orders": orders,
        "total_records": total_records,
        "total_pages": (total_records + 9) // 10,
        "current_page": page
    })

@app.route('/api/order/add', methods=['POST'])
@login_required
def api_add_order():
    insert_order(request.form.get('category'), float(request.form.get('amount', 0)))
    RealtimeService.sync_revenue_from_db() 
    return jsonify({"code": 200, "msg": "新增成功"})

@app.route('/api/order/update', methods=['POST'])
@login_required
def api_update_order():
    update_order(int(request.form.get('id')), request.form.get('category'), float(request.form.get('amount', 0)))
    RealtimeService.sync_revenue_from_db()
    return jsonify({"code": 200, "msg": "修改成功"})

@app.route('/api/order/delete/<int:order_id>')
@login_required
def api_delete_order(order_id):
    delete_order(order_id)
    RealtimeService.sync_revenue_from_db()
    return jsonify({"code": 200, "msg": "删除成功"})

@app.route('/api/offline-stats')
@login_required
def api_offline_stats():
    data = AnalyticsService.get_category_sales_ranking()
    return jsonify({"code": 200, "data": data})

if __name__ == '__main__':
    init_db()
    RealtimeService.sync_revenue_from_db()
    # 💡 确保 target 指向的函数名正确
    threading.Thread(target=background_sensor_simulator, daemon=True).start()
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
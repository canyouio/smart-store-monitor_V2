import pandas as pd
from collections import deque
from dao import get_all_orders_df, get_total_revenue

class AnalyticsService:
    @staticmethod
    def get_category_sales_ranking():
        df = get_all_orders_df()
        if df.empty:
            return {"categories": [], "values": []}
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        sales = df.groupby('category')['amount'].sum().reset_index(name='total_amount')
        sales = sales.sort_values(by='total_amount', ascending=False)
        return {
            "categories": sales['category'].tolist(),
            "values": [round(val, 2) for val in sales['total_amount'].tolist()]
        }

realtime_queue = deque(maxlen=30) 
store_state = {'revenue': 0.0, 'visitors': 142, 'current_inside': 8}

class RealtimeService:
    @staticmethod
    def sync_revenue_from_db():
        store_state['revenue'] = get_total_revenue()
    @staticmethod
    def get_current_state():
        return store_state
    @staticmethod
    def process_sensor_event(action):
        if action == 'enter':
            store_state['current_inside'] += 1
            store_state['visitors'] += 1
        elif action == 'exit':
            store_state['current_inside'] = max(0, store_state['current_inside'] - 1)
    @staticmethod
    def append_to_queue(time_str, count):
        realtime_queue.append({"time": time_str, "count": count})
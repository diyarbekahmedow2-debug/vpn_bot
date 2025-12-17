# Этот скрипт исправит simple_server.py
import re

with open('simple_server.py', 'r') as f:
    content = f.read()

# Заменяем старую функцию do_POST на исправленную
new_callback_code = '''
    def do_POST(self):
        """Обработка POST запросов (callback от Platega)"""
        if self.path == '/platega-callback':
            try:
                import json
                import sqlite3
                import logging
                logging.basicConfig(level=logging.INFO)
                logger = logging.getLogger(__name__)
                
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                data = json.loads(post_data.decode('utf-8'))
                logger.info(f"📨 Callback от Platega: {data}")
                
                # ВАЖНО: В callback от Platega:
                # 'payload' - это наш внутренний order_id (например, vpn_123456_...)
                # 'id' - это transaction_id в системе Platega (UUID)
                order_id = data.get("payload")  # Это ваш order_id!
                status = data.get("status")     # "CONFIRMED" или "CANCELED"
                platega_tx_id = data.get("id")  # Это ID транзакции Platega
                
                if order_id and status:
                    # Обновляем базу данных
                    conn = sqlite3.connect('vpn.db')
                    cursor = conn.cursor()
                    
                    new_status = "success" if status == "CONFIRMED" else "failed"
                    cursor.execute(
                        "UPDATE payments SET status = ?, platega_order_id = ? WHERE order_id = ?",
                        (new_status, platega_tx_id, order_id)
                    )
                    conn.commit()
                    conn.close()
                    
                    logger.info(f"✅ Обновлен статус {order_id}: {new_status} (Platega ID: {platega_tx_id})")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode())
                
            except Exception as e:
                logger.error(f"❌ Ошибка: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
'''

# Заменяем старую версию do_POST
pattern = r'def do_POST\(self\):.*?def do_GET'
replacement = new_callback_code + '\n\n    def do_GET'
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('simple_server.py', 'w') as f:
    f.write(content)

print("✅ simple_server.py исправлен! Callback теперь работает правильно")

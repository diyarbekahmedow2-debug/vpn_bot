#!/usr/bin/env python3
"""
Простой веб-сервер для callback Platega
Запуск: python simple_server.py
"""

import http.server
import socketserver
import json
import sqlite3
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORT = 8000

class PlategaHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        """Обработка POST запросов (callback от Platega)"""
        if self.path == '/platega-callback':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                data = json.loads(post_data.decode('utf-8'))
                logger.info(f"📨 Callback от Platega: {data}")
                
                order_id = data.get("payload")
                status = data.get("status")
                
                if order_id and status:
                    # Обновляем базу данных
                    conn = sqlite3.connect('vpn.db')
                    cursor = conn.cursor()
                    
                    new_status = "success" if status == "CONFIRMED" else "failed"
                    cursor.execute(
                        "UPDATE payments SET status = ? WHERE order_id = ?",
                        (new_status, order_id)
                    )
                    conn.commit()
                    conn.close()
                    
                    logger.info(f"✅ Обновлен статус {order_id}: {new_status}")
                
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
    
    def do_GET(self):
        """Обработка GET запросов (страницы VPN)"""
        if self.path.startswith('/vpn/'):
            # Извлекаем токен из URL
            token = self.path.split('/vpn/')[1].split('?')[0]
            
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>VPN Конфигурация</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
        .btn {{ 
            background: #4CAF50; color: white; padding: 15px 30px; 
            border: none; border-radius: 5px; font-size: 16px; 
            margin: 10px; cursor: pointer; text-decoration: none;
            display: inline-block;
        }}
        .btn-blue {{ background: #2196F3; }}
        .container {{ 
            max-width: 600px; margin: 0 auto; 
            padding: 30px; border-radius: 10px; 
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 VPN Конфигурация</h1>
        <p>Токен: <code>{token}</code></p>
        <p>Домен: <strong>secureprodaww.ru</strong></p>
        
        <button class="btn" onclick="downloadConfig()">⬇️ Скачать VPN конфиг</button>
        <br>
        <a href="happvpn://config/{token}" class="btn btn-blue">📱 Открыть в Happ VPN</a>
        
        <script>
        function downloadConfig() {{
            // Пример конфигурации VPN
            const config = `client
dev tun
proto udp
remote secureprodaww.ru 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-CBC
auth SHA256
verb 3

<ca>
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAK... (ваш сертификат)
-----END CERTIFICATE-----
</ca>

<cert>
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAK... (клиентский сертификат)
-----END CERTIFICATE-----
</cert>

<key>
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG... (приватный ключ)
-----END PRIVATE KEY-----
</key>

<tls-auth>
-----BEGIN OpenVPN Static key V1-----
{token}
-----END OpenVPN Static key V1-----
</tls-auth>`;
            
            const blob = new Blob([config], {{ type: 'application/x-openvpn-profile' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'vpn_config_{token[:8]}.ovpn';
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            alert('✅ Конфигурация скачана!');
        }}
        </script>
    </div>
</body>
</html>"""
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        
        elif self.path == '/':
            html = """<!DOCTYPE html>
<html>
<head><title>VPN Bot - Готов</title></head>
<body style="text-align:center; padding:50px;">
    <h1>✅ VPN Bot работает!</h1>
    <p>Домен: <strong>secureprodaww.ru</strong></p>
    <p>IP: <strong>5.61.33.66</strong></p>
    <p>Callback URL: <code>https://secureprodaww.ru/platega-callback</code></p>
    <p>Статус: 🟢 Активен</p>
</body>
</html>"""
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Отключаем стандартное логирование"""
        pass

# Запуск сервера
if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), PlategaHandler) as httpd:
        logger.info(f"🌐 Веб-сервер запущен на порту {PORT}")
        logger.info(f"📡 Домен: secureprodaww.ru")
        logger.info(f"🔄 Callback URL: http://secureprodaww.ru:8000/platega-callback")
        logger.info("Нажмите Ctrl+C для остановки")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Сервер остановлен")
            httpd.server_close()

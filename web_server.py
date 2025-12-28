#!/usr/bin/env python3
"""
Веб-сервер для обработки callback от Platega и выдачи VPN
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sqlite3
import logging
import json
import os
from datetime import datetime

app = FastAPI(title="VPN Bot Web Server")

# Конфигурация
WEB_URL = os.getenv('WEB_URL', 'https://secureprodaww.ru')
PRICE = int(os.getenv('PRICE', '100'))
VPN_DURATION = int(os.getenv('VPN_DURATION', '30'))

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Инициализация шаблонов
templates = Jinja2Templates(directory="templates")

def get_db():
    conn = sqlite3.connect('vpn.db')
    conn.row_factory = sqlite3.Row
    return conn

# Новые маршруты для страниц сайта
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Главная страница сайта"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "price": PRICE,
        "vpn_duration": VPN_DURATION
    })

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    """Страница Политики конфиденциальности"""
    return templates.TemplateResponse("privacy.html", {"request": request})

@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    """Страница Пользовательского соглашения"""
    return templates.TemplateResponse("terms.html", {"request": request})

# ===== СУЩЕСТВУЮЩИЕ МАРШРУТЫ (НЕ МЕНЯТЬ!) =====
@app.post("/platega-callback")
async def platega_callback(request: Request):
    """
    Callback от Platega - получение уведомлений об оплате
    """
    try:
        data = await request.json()
        logger.info(f"📨 Получен callback от Platega: {data}")
        
        # Извлекаем данные
        order_id = data.get("payload")  # Наш order_id
        status = data.get("status")     # "CONFIRMED" или "CANCELED"
        platega_id = data.get("id")     # ID транзакции Platega
        
        if not order_id:
            logger.error("❌ Нет order_id в callback")
            return JSONResponse({"status": "error", "message": "No order_id"})
        
        # Обновляем статус платежа в БД
        conn = get_db()
        cursor = conn.cursor()
        
        # Проверяем существование платежа
        cursor.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,))
        payment = cursor.fetchone()
        
        if not payment:
            logger.error(f"❌ Платеж {order_id} не найден")
            conn.close()
            return JSONResponse({"status": "error", "message": "Payment not found"})
        
        # Обновляем статус
        new_status = "success" if status == "CONFIRMED" else "failed"
        
        cursor.execute('''
            UPDATE payments 
            SET status = ?, completed_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        ''', (new_status, order_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Статус платежа {order_id} обновлен на '{new_status}'")
        return JSONResponse({"status": "ok"})
        
    except json.JSONDecodeError:
        logger.error("❌ Неверный JSON в запросе")
        return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)
    except Exception as e:
        logger.error(f"❌ Ошибка обработки callback: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/vpn/{token}")
async def vpn_config_page(token: str):
    """
    Страница с VPN конфигурацией
    """
    # Проверяем в базе
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, u.username, u.first_name 
        FROM payments p
        LEFT JOIN users u ON p.telegram_id = u.telegram_id
        WHERE p.vpn_token = ? AND p.status = 'success'
    ''', (token,))
    
    payment = cursor.fetchone()
    conn.close()
    
    if not payment:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>VPN - Ошибка</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .error { color: #ff0000; font-size: 24px; }
            </style>
        </head>
        <body>
            <h1 class="error">❌ Конфигурация не найдена</h1>
            <p>Возможно:</p>
            <ul>
                <li>Ссылка устарела</li>
                <li>Платеж не был завершен</li>
                <li>Срок действия истек</li>
            </ul>
            <p>Вернитесь в бота: <a href="https://t.me/sequrevpnbot">@sequrevpnbot</a></p>
        </body>
        </html>
        """)
    
    # Формируем HTML страницу
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>VPNhdh Конфигурация</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            
            .container {{
                background: white;
                border-radius: 20px;
                padding: 40px;
                max-width: 500px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
            }}
            
            h1 {{
                color: #333;
                margin-bottom: 20px;
                font-size: 28px;
            }}
            
            .status {{
                display: inline-block;
                background: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 14px;
                margin-bottom: 20px;
            }}
            
            .info {{
                text-align: left;
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            
            .info p {{
                margin: 10px 0;
                color: #555;
            }}
            
            .buttons {{
                display: flex;
                flex-direction: column;
                gap: 15px;
                margin-top: 30px;
            }}
            
            .btn {{
                display: block;
                padding: 16px 24px;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                transition: all 0.3s;
                text-align: center;
            }}
            
            .btn-primary {{
                background: #4CAF50;
                color: white;
            }}
            
            .btn-primary:hover {{
                background: #45a049;
                transform: translateY(-2px);
            }}
            
            .btn-secondary {{
                background: #667eea;
                color: white;
            }}
            
            .btn-secondary:hover {{
                background: #5a67d8;
                transform: translateY(-2px);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 VPN Конфигурация</h1>
            
            <div class="status">✅ Активна</div>
            
            <div class="info">
                <p><strong>👤 Пользователь:</strong> {payment['first_name'] or payment['username'] or 'N/A'}</p>
                <p><strong>💰 Сумма:</strong> {payment['amount']} RUB</p>
                <p><strong>📅 Дата:</strong> {payment['created_at']}</p>
                <p><strong>⏳ Действует:</strong> 30 дней</p>
            </div>
            
            <div class="buttons">
                <button class="btn btn-primary"><a class="btn btn-primary"  href="happ://crypt3/i+Wn1zuWxiYY4Za/ZUKPFI8N2zXzwh4Ezp+NhLTrCFLsmHIpVJue0yM6Ig1eyoYjdnXNGydjvk44/pQN5/jcsikmPx60zSYI519Z2dzbvbG4pBAfwNZvBwSGcyYYqAEdN1uGET/ZzfVfoCpsvELuWfJSOBMYZjKVNgTMynRM1dT9YwDx2JieZxk7b2rI8eAye5BmzjKiUcWAoO7N2v/3oIcUq8I+m23hIqm1dw4bpqPbDerpEDexM+y/dxp925PAOlA38IO/akGiKk1GGAA2dsJPO3WKttFy7TROkJvy2hakPItv+7ZseJWKlqDhI9XuXeRQevIYPNloxahDLivVS+qqLpmTsx53gySO0pDpQ4m08PlUU/iQcZmvDg9eM4UM+FxCSi2t1OMbOfmbtoiolGdrUPUhngJ6iIrvQyZVDZCo631DXHvYol3vyyfBjgcGUR4Eu/WfLDwmwfM0XWrG1tt9JiZhOY3diPUYCRBmHBWE4DKSPT7aj4VL/bQtCBZQ0ege3w/qhHZCLDv8nTse62ga2n10YmUxu6OMFKPDxTMnECU/RDE0CVnYD8k0ILm+2BLUxhOfgfim6cL+z7MnrLYLMrVGOhhv8biYwU9aBMPwiX7sSrOhGYBRswqTMnBDl8+mHnlvu0Ao0I5yUXceYLxrSf+xJwERXxfKY3AWEkQ=">
                    ПОДКЛЮЧИТЬ
                </a></button>
            </div>
        </div>
        
        <script>
            function downloadConfig() {{
                // Создаем конфигурацию VPN
                const config = `client
dev tun
proto udp
remote vpn.{WEB_URL.replace('https://', '')} 1194
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
MIID... (ваш сертификат)
-----END CERTIFICATE-----
</ca>

<cert>
-----BEGIN CERTIFICATE-----
MIID... (клиентский сертификат)
-----END CERTIFICATE-----
</cert>

<key>
-----BEGIN PRIVATE KEY-----
MIIE... (приватный ключ)
-----END PRIVATE KEY-----
</key>

<tls-auth>
-----BEGIN OpenVPN Static key V1-----
{token}
-----END OpenVPN Static key V1-----
</tls-auth>`;
                
                // Создаем Blob и скачиваем
                const blob = new Blob([config], {{ type: 'application/x-openvpn-profile' }});
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'vpn_config_{token[:8]}.ovpn';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                alert('✅ Конфигурация скачана! Импортируйте файл в ваше VPN приложение.');
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/success")
async def success_page():
    """Страница успешной оплаты"""
    return RedirectResponse("https://t.me/sequrevpnbot?start=success")

@app.get("/fail")
async def fail_page():
    """Страница неудачной оплаты"""
    return RedirectResponse("https://t.me/sequrevpnbot?start=fail")

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🌐 Запуск веб-сервера...")
    logger.info(f"📡 Домен: {WEB_URL}")
    logger.info("🔄 Callback URL: {WEB_URL}/platega-callback")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

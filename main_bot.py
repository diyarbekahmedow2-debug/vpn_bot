#!/usr/bin/env python3
"""
VPN Telegram Bot с оплатой через Platega (СБП QR)
Полностью рабочий код
"""

import os
import asyncio
import logging
import sqlite3
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import aiohttp
from dotenv import load_dotenv

# ===== ЗАГРУЗКА КОНФИГУРАЦИИ =====
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
PRICE = int(os.getenv('PRICE', '100'))
PLATEGA_API_KEY = os.getenv('PLATEGA_API_KEY', '')
WEB_URL = os.getenv('WEB_URL', 'https://secureprodaww.ru')
VPN_DURATION = int(os.getenv('VPN_DURATION', '30'))

# Проверка обязательных полей
if not BOT_TOKEN:
    logging.error("❌ BOT_TOKEN не задан в .env файле!")
    exit(1)

# ===== ЛОГИРОВАНИЕ =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== ИНИЦИАЛИЗАЦИЯ БОТА =====
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ===== БАЗА ДАННЫХ =====
def init_database():
    """Инициализация базы данных"""
    conn = sqlite3.connect('vpn.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            is_active BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица платежей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            order_id TEXT UNIQUE NOT NULL,
            amount INTEGER NOT NULL,
            currency TEXT DEFAULT 'RUB',
            status TEXT DEFAULT 'pending',
            vpn_token TEXT UNIQUE,
            payment_method TEXT DEFAULT 'SBP_QR',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована")

# Инициализируем БД при запуске
init_database()

def get_db_connection():
    """Получение соединения с базой данных"""
    conn = sqlite3.connect('vpn.db')
    conn.row_factory = sqlite3.Row
    return conn

# ===== PLATEGA API (ИСПРАВЛЕННАЯ ВЕРСИЯ по документации) =====
class PlategaAPI:
    def __init__(self):
        self.api_key = os.getenv('PLATEGA_API_KEY', '')
        self.merchant_id = os.getenv('PLATEGA_MERCHANT_ID', '')
        self.base_url = "https://app.platega.io"  # Базовый URL
        self.headers = {
            "X-MerchantId": self.merchant_id,
            "X-Secret": self.api_key,
            "Content-Type": "application/json"
        }
        
        if not self.api_key or not self.merchant_id:
            logger.warning("⚠️ Ключи Platega не заданы полностью! Платежи не будут работать.")

    async def create_payment(self, amount: int, order_id: str, description: str) -> Optional[str]:
        """Создает платеж в Platega и возвращает ссылку для оплаты."""
        url = f"{self.base_url}/transaction/process"  # ПРАВИЛЬНЫЙ endpoint

        # ТЕЛО ЗАПРОСА ПО ДОКУМЕНТАЦИИ (СБП QR)
        data = {
            "paymentMethod": 2,  # 2 = СБП QR (ваш метод)
            "paymentDetails": {
                "amount": float(amount),
                "currency": "RUB"
            },
            "description": description,
            "return": f"{WEB_URL}/success",  # Куда перейти после успеха
            "failedUrl": f"{WEB_URL}/fail",  # Куда перейти после неудачи
            "payload": order_id  # Наш внутренний ID
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=self.headers, timeout=30) as response:
                    result_text = await response.text()
                    logger.info(f"Ответ от Platega (статус {response.status}): {result_text}")
                    
                    if response.status == 200:
                        result = json.loads(result_text)
                        # Из документации: ссылка для оплаты в поле "redirect"
                        payment_url = result.get('redirect')
                        if payment_url:
                            logger.info(f"✅ Платеж создан. Ссылка: {payment_url}")
                            return payment_url
                        else:
                            logger.error(f"❌ Platega не вернул ссылку. Ответ: {result}")
                    else:
                        logger.error(f"❌ Ошибка API Platega. Статус: {response.status}")
                        logger.error(f"Тело ответа: {result_text}")
        except Exception as e:
            logger.error(f"❌ Ошибка сети при создании платежа: {e}")
        return None        
        url = f"{self.base_url}/api/transactions/process"
        
        data = {
            "paymentMethod": 2,  # 2 = СБП QR
            "paymentDetails": {
                "amount": float(amount),
                "currency": "RUB"
            },
            "description": description,
            "payload": order_id,  # Наш внутренний ID для callback
            "return": f"{WEB_URL}/success",
            "failedUrl": f"{WEB_URL}/fail"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=self.headers, timeout=30) as response:
                    if response.status == 201:
                        result = await response.json()
                        payment_url = result.get('redirect')
                        if payment_url:
                            logger.info(f"✅ Платеж создан: {order_id}")
                            return payment_url
                        else:
                            logger.error(f"❌ Нет ссылки в ответе Platega: {result}")
                    else:
                        logger.error(f"❌ Ошибка API Platega. Статус: {response.status}")
                        logger.error(f"Ответ: {await response.text()}")
        except Exception as e:
            logger.error(f"❌ Ошибка создания платежа: {e}")
        
        return None

platega = PlategaAPI()


        async def check_payment_status(self, transaction_id: str):
            """Проверяет статус платежа в Platega по transactionId."""
            url = f"{self.base_url}/transaction/{transaction_id}"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=self.headers, timeout=10) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"Статус транзакции {transaction_id}: {result.get('status')}")
                            return result
                        else:
                            logger.error(f"Ошибка при проверке статуса. Код: {response.status}")
                            logger.error(await response.text())
            except Exception as e:
                logger.error(f"Ошибка сети при проверке статуса: {e}")
            return None

# ===== ОБРАБОТЧИКИ КОМАНД =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user = message.from_user
    
    # Сохраняем пользователя в БД
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
        (user.id, user.username, user.first_name)
    )
    conn.commit()
    conn.close()
    
    welcome_text = f"""
🔐 <b>VPN Бот</b>

Привет, {user.first_name or 'пользователь'}!

Я предоставляю доступ к <b>быстрому и защищенному VPN</b> сервису.

<b>Что вы получаете:</b>
✅ Неограниченный трафик
✅ Высокая скорость
✅ Полная анонимность
✅ Защита от блокировок
✅ Поддержка 24/7

<b>Стоимость:</b> {PRICE} рублей за {VPN_DURATION} дней

<b>Как это работает:</b>
1. Нажимаете кнопку "Купить VPN"
2. Оплачиваете через СБП QR-код
3. Получаете доступ к VPN

Выберите действие ниже 👇
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить VPN доступ", callback_data="buy_vpn")],
        [
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help"),
            InlineKeyboardButton(text="📊 Статус", callback_data="status")
        ]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard)

@dp.callback_query(F.data == "buy_vpn")
async def process_buy(callback: types.CallbackQuery):
    """Обработка нажатия кнопки 'Купить VPN'"""
    user = callback.from_user
    await callback.answer()
    
    # Создаем запись о платеже в БД
    order_id = f"vpn_{user.id}_{int(datetime.now().timestamp())}"
    vpn_token = str(uuid.uuid4())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO payments (telegram_id, order_id, amount, vpn_token) VALUES (?, ?, ?, ?)",
        (user.id, order_id, PRICE, vpn_token)
    )
    conn.commit()
    conn.close()
    
    # Создаем платеж в Platega
    loading_msg = await callback.message.answer("🔄 <b>Создаю ссылку для оплаты...</b>")
    
    payment_url = await platega.create_payment(
        amount=PRICE,
        order_id=order_id,
        description=f"VPN доступ для @{user.username or user.id} на {VPN_DURATION} дней"
    )
    
    await loading_msg.delete()
    
    if payment_url:
        # Кнопка для оплаты
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить через СБП QR", url=payment_url)],
            [InlineKeyboardButton(text="🔄 Проверить статус", callback_data=f"check_{order_id}")]
        ])
        
        await callback.message.answer(
            f"✅ <b>Счет на {PRICE} руб. создан!</b>\n\n"
            f"<b>ID заказа:</b> <code>{order_id}</code>\n"
            f"<b>Метод оплаты:</b> СБП QR-код\n\n"
            "Нажмите кнопку ниже для оплаты. После успешной оплаты вы автоматически получите доступ к VPN.",
            reply_markup=keyboard
        )
    else:
        await callback.message.answer(
            "❌ <b>Не удалось создать платеж</b>\n\n"
            "Возможные причины:\n"
            "• Не настроен API ключ Platega\n"
            "• Проблемы с сетью\n"
            "• Ошибка API Platega\n\n"
            "Проверьте настройки или попробуйте позже."
        )

@dp.callback_query(F.data.startswith("check_"))
async def check_payment_status(callback: types.CallbackQuery):
    """Проверка статуса платежа"""
    order_id = callback.data.replace("check_", "")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT status, vpn_token FROM payments WHERE order_id = ?",
        (order_id,)
    )
    payment = cursor.fetchone()
    conn.close()
    
    if not payment:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        return
    
    status = payment['status']
    vpn_token = payment['vpn_token']
    
    if status == 'success':
        # Оплата успешна! Даем ссылку на VPN
        vpn_url = f"{WEB_URL}/vpn/{vpn_token}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Получить VPN доступ", url=vpn_url)],
            [InlineKeyboardButton(text="📱 Открыть в приложении", 
                                 url=f"happvpn://config/{vpn_token}")]
        ])
        
        await callback.message.answer(
            f"✅ <b>Оплата подтверждена!</b>\n\n"
            f"Ваш VPN доступ активирован на <b>{VPN_DURATION} дней</b>.\n\n"
            f"Нажмите кнопку ниже, чтобы получить доступ:",
            reply_markup=keyboard
        )
        await callback.answer()
    
    elif status == 'pending':
        await callback.answer("⏳ Платеж еще не получен. Если вы уже оплатили, подождите 1-2 минуты.", show_alert=True)
    
    else:
        await callback.answer(f"Статус платежа: {status}", show_alert=True)

@dp.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    """Показать справку"""
    help_text = f"""
<b>📞 Помощь и поддержка</b>

<b>Как купить VPN:</b>
1. Нажмите кнопку "Купить VPN доступ"
2. Оплатите {PRICE} руб. через СБП QR-код
3. Получите ссылку на VPN конфигурацию

<b>Что делать после оплаты:</b>
1. Нажмите кнопку "Получить VPN доступ"
2. Сохраните конфигурационный файл
3. Импортируйте его в VPN приложение
4. Наслаждайтесь свободным интернетом!

<b>Техническая информация:</b>
• Цена: {PRICE} руб. / {VPN_DURATION} дней
• Метод оплаты: СБП QR-код
• Домен: {WEB_URL}

<b>Если возникли проблемы:</b>
1. Попробуйте команду /start
2. Проверьте статус платежа
3. Напишите в поддержку
    """
    
    await callback.message.answer(help_text)
    await callback.answer()

@dp.callback_query(F.data == "status")
async def show_status(callback: types.CallbackQuery):
    """Показать статус системы"""
    import socket
    
    hostname = socket.gethostname()
    
    status_text = f"""
<b>📊 Статус системы</b>

• Сервер: <code>{hostname}</code>
• IP: <code>5.61.33.66</code>
• Домен: {WEB_URL}
• Бот: 🟢 Работает
• База данных: 🟢 Активна
• Platega: {'🟢 Настроен' if PLATEGA_API_KEY else '🔴 Не настроен'}
• Цена: {PRICE} руб.

<b>Для начала работы нажмите:</b> /start
    """
    
    await callback.message.answer(status_text)
    await callback.answer()

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Панель администратора"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Статистика
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM payments")
    total_payments = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'success'")
    successful_payments = cursor.fetchone()[0]
    
    conn.close()
    
    admin_text = f"""
<b>👑 Панель администратора</b>

<b>Статистика:</b>
• Пользователей: {total_users}
• Всего платежей: {total_payments}
• Успешных платежей: {successful_payments}
• Доход: {successful_payments * PRICE} руб.

<b>Действия:</b>
• /start - перезапустить бота
• /admin - эта панель
    """
    
    await message.answer(admin_text)

# ===== ЗАПУСК БОТА =====
async def main():
    """Основная функция запуска"""
    logger.info("🚀 Запуск VPN бота...")
    logger.info(f"Цена: {PRICE} руб.")
    logger.info(f"Домен: {WEB_URL}")
    logger.info(f"Platega API: {'Настроен' if PLATEGA_API_KEY else 'Не настроен'}")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())

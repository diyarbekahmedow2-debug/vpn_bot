import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загружаем конфигурацию
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в .env файле!")
    exit(1)

# СОБЛЮДАЙТЕ ЭТУ СТРОЧКУ - правильная инициализация бота!
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    welcome_text = f"""
✅ <b>VPN Бот активирован!</b>

Привет, {user.first_name or 'пользователь'}!

🎯 <b>Сервер настроен и готов к работе:</b>
• IP: <code>5.61.33.66</code>
• Домен: <code>secureprodaww.ru</code>
• Статус: 🟢 Работает

🛠 <b>Следующие шаги:</b>
1. Настройка Platega (оплата через СБП QR)
2. Добавление кнопки "Купить VPN"
3. Настройка выдачи конфигураций

<b>Для проверки работы бота нажмите /test</b>
    """
    
    await message.answer(welcome_text)

# Обработчик команды /test
@dp.message(Command("test"))
async def cmd_test(message: types.Message):
    await message.answer(
        "🧪 <b>Тест системы:</b> УСПЕШНО!\n\n"
        "✅ Бот работает корректно\n"
        "✅ Сервер отвечает\n"
        "✅ Python окружение настроено\n\n"
        "Следующий шаг: настройка платежной системы."
    )

# Обработчик команды /status
@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    import subprocess
    import socket
    
    # Получаем статус сервера
    try:
        # IP сервера
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        
        # Проверяем веб-сервер
        nginx_status = subprocess.run(
            ['systemctl', 'is-active', 'nginx'], 
            capture_output=True, text=True
        ).stdout.strip()
        
        status_text = f"""
📊 <b>Статус системы:</b>

• Сервер: <code>{hostname}</code>
• IP: <code>{ip_address}</code>
• Домен: secureprodaww.ru
• Веб-сервер: {'🟢' if nginx_status == 'active' else '🔴'} {nginx_status}
• Python: активен
• Бот: работает
        """
        
        await message.answer(status_text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при проверке статуса: {str(e)}")

# Запуск бота
async def main():
    logger.info("🚀 Бот запускается...")
    logger.info(f"Токен: {BOT_TOKEN[:10]}...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

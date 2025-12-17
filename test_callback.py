#!/usr/bin/env python3
"""
Тестовый скрипт для проверки callback
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверяем структуру базы данных
conn = sqlite3.connect('vpn.db')
cursor = conn.cursor()

print("📊 Проверка базы данных:")
print("=" * 50)

# 1. Проверяем таблицы
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Таблицы в базе: {[t[0] for t in tables]}")

# 2. Проверяем структуру таблицы payments
try:
    cursor.execute("PRAGMA table_info(payments)")
    columns = cursor.fetchall()
    print("\nСтруктура таблицы payments:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
except:
    print("\n❌ Таблица payments не существует!")

# 3. Показываем существующие платежи
try:
    cursor.execute("SELECT order_id, status, platega_order_id FROM payments LIMIT 5")
    payments = cursor.fetchall()
    print(f"\nПоследние платежи ({len(payments)}):")
    for p in payments:
        print(f"  Order: {p[0]}, Status: {p[1]}, Platega ID: {p[2]}")
except:
    print("\n❌ Не удалось получить платежи")

conn.close()

print("\n" + "=" * 50)
print("✅ Проверка завершена")
print("\n📋 Что делать дальше:")
print("1. Запустите веб-сервер: python simple_server.py")
print("2. Запустите бота: python main_bot.py")
print("3. В Telegram нажмите 'Купить VPN доступ'")
print("4. Перейдите по ссылке и оплатите")
print("5. Проверьте логи simple_server.py - должен прийти callback")

#!/bin/bash
# Скрипт безопасного обновления на сервере

echo "🔧 Начинаем обновление VPN бота..."

# 1. Сохраняем текущие настройки
cp .env .env.backup
cp vpn.db vpn.db.backup

# 2. Останавливаем службы
sudo systemctl stop vpn-bot.service
sudo systemctl stop vpn-web.service

# 3. Получаем обновления из GitHub
git pull origin main

# 4. Восстанавливаем настройки
cp .env.backup .env
cp vpn.db.backup vpn.db

# 5. Обновляем зависимости
pip install -r requirements.txt

# 6. Запускаем службы
sudo systemctl start vpn-web.service
sudo systemctl start vpn-bot.service

echo "✅ Обновление завершено!"
echo "📊 Статус служб:"
sudo systemctl status vpn-bot.service --no-pager -l
sudo systemctl status vpn-web.service --no-pager -l

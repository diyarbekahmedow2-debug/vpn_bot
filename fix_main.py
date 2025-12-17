# Этот скрипт автоматически добавит метод check_payment_status в main_bot.py
import re

with open('main_bot.py', 'r') as f:
    content = f.read()

# Ищем место, где заканчивается метод create_payment и вставляем новый метод
new_method = '''
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
'''

# Вставляем новый метод после create_payment
pattern = r'(async def create_payment\(.*?)(?=\n    async def|\nclass|\ndef|\n# =====)'
replacement = r'\1\n' + new_method
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('main_bot.py', 'w') as f:
    f.write(content)

print("✅ main_bot.py исправлен! Добавлен метод check_payment_status")

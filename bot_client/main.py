import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.config import settings
from core.logger import setup_logger
from core.database import init_db
from bot_client.handlers import start, booking, subscriptions, profile

logger = setup_logger("bot_client")

async def main():
    logger.info("Starting Client Bot")
    
    # Инициализация БД
    await init_db()
    
    # Создание бота
    bot = Bot(
        token=settings.BOT_CLIENT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Хранилище для FSM
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(booking.router)
    dp.include_router(subscriptions.router)
    dp.include_router(profile.router)
    
    # Запуск
    try:
        if settings.USE_WEBHOOK:
            await bot.set_webhook(f"{settings.WEBHOOK_URL}/client")
            logger.info(f"Webhook set to {settings.WEBHOOK_URL}/client")
        else:
            await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

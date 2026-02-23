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
from bot_owner.handlers import dashboard, clients, settings as owner_settings

logger = setup_logger("bot_owner")

async def main():
    logger.info("Starting Owner Bot")
    
    await init_db()
    
    bot = Bot(
        token=settings.BOT_OWNER_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутеров
    dp.include_router(dashboard.router)
    dp.include_router(clients.router)
    dp.include_router(owner_settings.router)
    
    try:
        if settings.USE_WEBHOOK:
            await bot.set_webhook(f"{settings.WEBHOOK_URL}/owner")
        else:
            await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

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
from bot_employee.handlers import auth, admin, washer
from bot_employee.middleware import RoleMiddleware

logger = setup_logger("bot_employee")

async def main():
    logger.info("Starting Employee Bot")
    
    await init_db()
    
    bot = Bot(
        token=settings.BOT_EMPLOYEE_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    
    # Middleware для проверки ролей
    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())
    
    # Регистрация роутеров
    dp.include_router(auth.router)
    dp.include_router(admin.router)
    dp.include_router(washer.router)
    
    try:
        if settings.USE_WEBHOOK:
            await bot.set_webhook(f"{settings.WEBHOOK_URL}/employee")
        else:
            await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

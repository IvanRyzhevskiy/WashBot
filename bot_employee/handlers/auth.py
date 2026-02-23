from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from bot_employee.keyboards import get_admin_keyboard, get_washer_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, user: dict, user_role: str):
    """Вход в бот сотрудников"""
    
    if user_role == "admin":
        await message.answer(
            f"👋 Здравствуйте, {user.full_name}!\n\n"
            f"Вы вошли как <b>Администратор</b>.",
            reply_markup=get_admin_keyboard()
        )
    elif user_role == "washer":
        await message.answer(
            f"👋 Здравствуйте, {user.full_name}!\n\n"
            f"Вы вошли как <b>Мойщик</b>.",
            reply_markup=get_washer_keyboard()
        )
    else:
        await message.answer("❌ Доступ запрещен.")

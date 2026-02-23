from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from core.database import get_db_context
from core.models import User, CarWash
from bot_client.keyboards import get_main_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()
    
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username
    
    async with get_db_context() as db:
        # Поиск пользователя
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Создание нового пользователя
            result = await db.execute(select(CarWash))
            carwash = result.scalar_one()
            
            user = User(
                telegram_id=telegram_id,
                car_wash_id=carwash.id,
                role="client",
                full_name=full_name,
                username=username,
                balance=0
            )
            db.add(user)
            await db.commit()
            
            welcome = f"👋 Добро пожаловать, {full_name}!"
        else:
            welcome = f"👋 С возвращением, {full_name}!"
    
    await message.answer(
        f"{welcome}\n\n"
        f"Я помогу вам записаться на мойку, купить абонемент и следить за бонусами.",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "◀️ Назад")
async def cmd_back(message: Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "back_to_main")
async def callback_back(callback: CallbackQuery, state: FSMContext):
    """Возврат через callback"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

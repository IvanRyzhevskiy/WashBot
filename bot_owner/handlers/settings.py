from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from core.database import get_db_context
from core.models import Service, CarWash, User
from bot_owner.keyboards import get_settings_keyboard

router = Router()

class ServiceStates(StatesGroup):
    name = State()
    description = State()
    price = State()
    duration = State()

@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message):
    """Меню настроек"""
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_settings_keyboard()
    )

@router.callback_query(F.data == "settings_services")
async def list_services(callback: CallbackQuery):
    """Список услуг"""
    telegram_id = callback.from_user.id
    
    async with get_db_context() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        owner = result.scalar_one()
        
        result = await db.execute(
            select(Service)
            .where(Service.car_wash_id == owner.car_wash_id)
            .order_by(Service.name)
        )
        services = result.scalars().all()
    
    text = "🧼 <b>Услуги:</b>\n\n"
    
    for s in services:
        status = "✅" if s.is_active else "❌"
        text += f"{status} <b>{s.name}</b>\n"
        text += f"   {s.price}₽ | {s.duration} мин\n"
    
    text += "\nЧтобы добавить услугу, введите:\n/add_service"
    
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(F.text == "/add_service")
async def add_service_start(message: Message, state: FSMContext):
    """Добавление услуги"""
    await state.set_state(ServiceStates.name)
    await message.answer("Введите название услуги:")

@router.message(ServiceStates.name)
async def add_service_name(message: Message, state: FSMContext):
    """Ввод названия"""
    await state.update_data(name=message.text)
    await state.set_state(ServiceStates.description)
    await message.answer("Введите описание услуги (или '-' если не нужно):")

@router.message(ServiceStates.description)
async def add_service_description(message: Message, state: FSMContext):
    """Ввод описания"""
    description = None if message.text == "-" else message.text
    await state.update_data(description=description)
    await state.set_state(ServiceStates.price)
    await message.answer("Введите стоимость (в рублях):")

@router.message(ServiceStates.price)
async def add_service_price(message: Message, state: FSMContext):
    """Ввод цены"""
    try:
        price = float(message.text)
    except ValueError:
        await message.answer("❌ Введите число")
        return
    
    await state.update_data(price=price)
    await state.set_state(ServiceStates.duration)
    await message.answer("Введите длительность (в минутах):")

@router.message(ServiceStates.duration)
async def add_service_duration(message: Message, state: FSMContext, user: dict):
    """Ввод длительности и сохранение"""
    try:
        duration = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число")
        return
    
    data = await state.get_data()
    
    async with get_db_context() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        owner = result.scalar_one()
        
        service = Service(
            car_wash_id=owner.car_wash_id,
            name=data["name"],
            description=data.get("description"),
            price=data["price"],
            duration=duration,
            is_active=True
        )
        db.add(service)
        await db.commit()
    
    await message.answer(f"✅ Услуга '{data['name']}' добавлена!")
    await state.clear()

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select, desc

from core.database import get_db_context
from core.models import User, Appointment, Service, Subscription

router = Router()

@router.message(F.text == "⭐ Мои записи")
async def my_appointments(message: Message):
    """История записей"""
    telegram_id = message.from_user.id
    
    async with get_db_context() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one()
        
        result = await db.execute(
            select(Appointment)
            .where(Appointment.user_id == user.id)
            .order_by(desc(Appointment.appointment_time))
            .limit(10)
        )
        appointments = result.scalars().all()
    
    if not appointments:
        await message.answer("У вас пока нет записей.")
        return
    
    text = "📋 <b>Ваши последние записи:</b>\n\n"
    
    for apt in appointments:
        async with get_db_context() as db:
            result = await db.execute(
                select(Service).where(Service.id == apt.service_id)
            )
            service = result.scalar_one()
        
        date_str = apt.appointment_time.strftime("%d.%m.%Y %H:%M")
        status_emoji = {
            "confirmed": "✅",
            "completed": "✔️",
            "cancelled": "❌"
        }.get(apt.status, "⏳")
        
        text += f"{status_emoji} {date_str} - {service.name}\n"
    
    await message.answer(text)

@router.message(F.text == "📞 Контакты")
async def contacts(message: Message):
    """Контактная информация"""
    telegram_id = message.from_user.id
    
    async with get_db_context() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one()
        
        result = await db.execute(
            select(CarWash).where(CarWash.id == user.car_wash_id)
        )
        carwash = result.scalar_one()
    
    text = (
        f"🏢 <b>{carwash.name}</b>\n\n"
        f"📍 Адрес: {carwash.address}\n"
        f"📞 Телефон: {carwash.phone}\n\n"
        f"🕐 График работы:\n"
    )
    
    # Форматируем график работы
    days = {
        "mon": "Пн", "tue": "Вт", "wed": "Ср",
        "thu": "Чт", "fri": "Пт", "sat": "Сб", "sun": "Вс"
    }
    
    for day_key, day_name in days.items():
        hours = carwash.working_hours.get(day_key, "выходной")
        text += f"{day_name}: {hours}\n"
    
    await message.answer(text)

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime, date, timedelta
from sqlalchemy import select, func

from core.database import get_db_context
from core.models import Appointment, User, Service
from bot_employee.keyboards import get_appointment_complete_keyboard

router = Router()

@router.message(F.text == "🚗 Мои записи")
async def my_appointments(message: Message, user: dict):
    """Показать записи мойщика"""
    
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    
    async with get_db_context() as db:
        result = await db.execute(
            select(Appointment)
            .where(
                Appointment.car_wash_id == user.car_wash_id,
                Appointment.appointment_time >= today_start,
                Appointment.appointment_time <= today_end,
                Appointment.status == "confirmed"
            )
            .order_by(Appointment.appointment_time)
        )
        appointments = result.scalars().all()
    
    if not appointments:
        await message.answer("🚗 На сегодня записей нет.")
        return
    
    for apt in appointments:
        async with get_db_context() as db:
            result = await db.execute(
                select(User).where(User.id == apt.user_id)
            )
            client = result.scalar_one()
            
            result = await db.execute(
                select(Service).where(Service.id == apt.service_id)
            )
            service = result.scalar_one()
        
        time_str = apt.appointment_time.strftime("%H:%M")
        text = (
            f"🕐 {time_str} - {client.full_name}\n"
            f"{service.name} - {service.duration} мин"
        )
        
        await message.answer(
            text,
            reply_markup=get_appointment_complete_keyboard(apt.id)
        )

@router.callback_query(F.data.startswith("complete:"))
async def mark_completed(callback: CallbackQuery, user: dict):
    """Отметить выполнение"""
    apt_id = int(callback.data.split(":")[1])
    
    async with get_db_context() as db:
        result = await db.execute(
            select(Appointment).where(Appointment.id == apt_id)
        )
        apt = result.scalar_one()
        
        if apt.status == "completed":
            await callback.answer("Уже выполнено", show_alert=True)
            return
        
        apt.status = "completed"
        apt.completed_at = datetime.now()
        await db.commit()
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ <b>ВЫПОЛНЕНО</b>"
    )
    await callback.answer("Отмечено как выполненное")

@router.message(F.text == "📊 Моя статистика")
async def my_stats(message: Message, user: dict):
    """Статистика мойщика"""
    
    today_start = datetime.combine(date.today(), datetime.min.time())
    week_ago = datetime.now() - timedelta(days=7)
    
    async with get_db_context() as db:
        # За сегодня
        result = await db.execute(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.car_wash_id == user.car_wash_id,
                Appointment.status == "completed",
                Appointment.completed_at >= today_start
            )
        )
        today_count = result.scalar() or 0
        
        # За неделю
        result = await db.execute(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.car_wash_id == user.car_wash_id,
                Appointment.status == "completed",
                Appointment.completed_at >= week_ago
            )
        )
        week_count = result.scalar() or 0
    
    await message.answer(
        f"📊 <b>Ваша статистика</b>\n\n"
        f"✅ Выполнено сегодня: {today_count}\n"
        f"📅 Выполнено за неделю: {week_count}"
    )

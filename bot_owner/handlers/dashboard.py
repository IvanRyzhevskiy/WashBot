from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime, date, timedelta
from sqlalchemy import select, func

from core.database import get_db_context
from core.models import Appointment, User, Service, Transaction

router = Router()

@router.message(F.text == "📊 Дашборд")
async def show_dashboard(message: Message):
    """Показать дашборд.
    Выручка рассчитывается по завершённым записям (Appointment.status == 'completed') —
    это учёт фактически оказанных услуг.
    Дополнительно выводится разбивка выручки по услугам за последний месяц.
    """
    telegram_id = message.from_user.id
    
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    async with get_db_context() as db:
        # Получаем владельца и его мойку
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        owner = result.scalar_one()
        car_wash_id = owner.car_wash_id
        
        # Выручка сегодня (оказанные услуги)
        result = await db.execute(
            select(func.coalesce(func.sum(Service.price), 0))
            .select_from(Appointment)
            .join(Service, Appointment.service_id == Service.id)
            .where(
                Appointment.car_wash_id == car_wash_id,
                Appointment.status == "completed",
                Appointment.completed_at >= today_start
            )
        )
        revenue_today = result.scalar()
        
        # Выручка за неделю
        result = await db.execute(
            select(func.coalesce(func.sum(Service.price), 0))
            .select_from(Appointment)
            .join(Service, Appointment.service_id == Service.id)
            .where(
                Appointment.car_wash_id == car_wash_id,
                Appointment.status == "completed",
                func.date(Appointment.completed_at) >= week_ago
            )
        )
        revenue_week = result.scalar()
        
        # Выручка за месяц
        result = await db.execute(
            select(func.coalesce(func.sum(Service.price), 0))
            .select_from(Appointment)
            .join(Service, Appointment.service_id == Service.id)
            .where(
                Appointment.car_wash_id == car_wash_id,
                Appointment.status == "completed",
                func.date(Appointment.completed_at) >= month_ago
            )
        )
        revenue_month = result.scalar()
        
        # Количество записей сегодня
        result = await db.execute(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.car_wash_id == car_wash_id,
                func.date(Appointment.appointment_time) == today
            )
        )
        appointments_today = result.scalar()
        
        # Количество клиентов
        result = await db.execute(
            select(func.count())
            .select_from(User)
            .where(
                User.car_wash_id == car_wash_id,
                User.role == "client"
            )
        )
        clients_count = result.scalar()
        
        # Ожидающие платежи (pending + client_confirmed)
        result = await db.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.car_wash_id == car_wash_id,
                Transaction.status.in_(["pending", "client_confirmed"])
            )
        )
        pending_payments = result.scalar()
        
        # Разбивка выручки по услугам за последний месяц
        result = await db.execute(
            select(Service.name, func.coalesce(func.sum(Service.price), 0).label("revenue"))
            .select_from(Appointment)
            .join(Service, Appointment.service_id == Service.id)
            .where(
                Appointment.car_wash_id == car_wash_id,
                Appointment.status == "completed",
                func.date(Appointment.completed_at) >= month_ago
            )
            .group_by(Service.id, Service.name)
            .order_by(func.sum(Service.price).desc())
        )
        service_revenue = result.all()
    
    # Формируем текст разбивки по услугам
    if service_revenue:
        service_lines = "\n".join(
            f"  • {name}: {float(rev):,.0f}₽" for name, rev in service_revenue
        )
        service_breakdown = f"\n\n🧼 <b>По услугам за месяц:</b>\n{service_lines}"
    else:
        service_breakdown = ""
    
    await message.answer(
        f"📊 <b>Дашборд</b>\n\n"
        f"💰 <b>Выручка (оказанные услуги):</b>\n"
        f"• Сегодня: {revenue_today:,.0f}₽\n"
        f"• Неделя: {revenue_week:,.0f}₽\n"
        f"• Месяц: {revenue_month:,.0f}₽\n\n"
        f"📅 <b>Записи сегодня:</b> {appointments_today}\n"
        f"👥 <b>Клиентов всего:</b> {clients_count}\n"
        f"⏳ <b>Ожидают оплаты:</b> {pending_payments}"
        f"{service_breakdown}"
    )

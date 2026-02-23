from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime, date
from sqlalchemy import select, and_

from core.database import get_db_context
from core.models import Appointment, User, Service, Transaction, Subscription
from bot_employee.keyboards import get_payment_keyboard

router = Router()

@router.message(F.text == "📅 Записи на сегодня")
async def show_today_appointments(message: Message, user: dict):
    """Показать записи на сегодня"""
    
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    
    async with get_db_context() as db:
        result = await db.execute(
            select(Appointment)
            .where(
                Appointment.car_wash_id == user.car_wash_id,
                Appointment.appointment_time >= today_start,
                Appointment.appointment_time <= today_end,
                Appointment.status.in_(["confirmed", "pending"])
            )
            .order_by(Appointment.appointment_time)
        )
        appointments = result.scalars().all()
    
    if not appointments:
        await message.answer("📅 На сегодня записей нет.")
        return
    
    text = "📅 <b>Записи на сегодня:</b>\n\n"
    
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
        text += f"🕐 {time_str} - {client.full_name}\n"
        text += f"   {service.name} - {service.price}₽\n"
        text += f"   Статус: {apt.status}\n\n"
        
        # Ограничим количество, чтобы не превысить лимит сообщения
        if len(text) > 3000:
            await message.answer(text)
            text = ""
    
    if text:
        await message.answer(text)

@router.message(F.text == "💰 Платежи")
async def show_payments(message: Message, user: dict):
    """Показать ожидающие платежи"""
    
    async with get_db_context() as db:
        result = await db.execute(
            select(Transaction)
            .where(
                Transaction.car_wash_id == user.car_wash_id,
                Transaction.status == "pending"
            )
            .order_by(Transaction.created_at.desc())
        )
        transactions = result.scalars().all()
    
    if not transactions:
        await message.answer("💰 Нет ожидающих платежей.")
        return
    
    for txn in transactions:
        async with get_db_context() as db:
            result = await db.execute(
                select(User).where(User.id == txn.user_id)
            )
            client = result.scalar_one()
        
        text = (
            f"💰 <b>Платеж #{txn.id}</b>\n\n"
            f"Клиент: {client.full_name}\n"
            f"Сумма: {txn.amount}₽\n"
            f"Тип: {txn.type}\n"
            f"Дата: {txn.created_at.strftime('%d.%m.%Y %H:%M')}"
        )
        
        await message.answer(
            text,
            reply_markup=get_payment_keyboard(txn.id)
        )

@router.callback_query(F.data.startswith("approve_pay:"))
async def approve_payment(callback: CallbackQuery, user: dict):
    """Подтверждение платежа"""
    txn_id = int(callback.data.split(":")[1])
    
    async with get_db_context() as db:
        result = await db.execute(
            select(Transaction).where(Transaction.id == txn_id)
        )
        txn = result.scalar_one()
        
        if txn.status != "pending":
            await callback.answer("Платеж уже обработан", show_alert=True)
            return
        
        txn.status = "approved"
        txn.admin_id = user.id
        txn.approved_at = datetime.now()
        
        # Начисляем абонемент или пополняем баланс
        if txn.type == "subscription_purchase":
            # Создаем абонемент (упрощенно)
            subscription = Subscription(
                user_id=txn.user_id,
                car_wash_id=txn.car_wash_id,
                name="Абонемент",
                total_washes=5,
                remaining_washes=5,
                purchase_price=txn.amount,
                valid_until=datetime.now().date() + timedelta(days=30),
                is_active=True
            )
            db.add(subscription)
        else:
            # Пополнение баланса
            result = await db.execute(
                select(User).where(User.id == txn.user_id)
            )
            client = result.scalar_one()
            client.balance += txn.amount
        
        await db.commit()
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ Платеж подтвержден!"
    )
    await callback.answer("Платеж подтвержден")

@router.callback_query(F.data.startswith("reject_pay:"))
async def reject_payment(callback: CallbackQuery, user: dict):
    """Отклонение платежа"""
    txn_id = int(callback.data.split(":")[1])
    
    async with get_db_context() as db:
        result = await db.execute(
            select(Transaction).where(Transaction.id == txn_id)
        )
        txn = result.scalar_one()
        
        txn.status = "rejected"
        txn.admin_id = user.id
        await db.commit()
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n❌ Платеж отклонен!"
    )
    await callback.answer("Платеж отклонен")

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

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
        # Загружаем клиента и услугу за один запрос (нет N+1)
        result = await db.execute(
            select(Appointment)
            .options(selectinload(Appointment.user), selectinload(Appointment.service))
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
        client = apt.user
        service = apt.service
        
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
    """Показать платежи, ожидающие подтверждения администратора.
    Отображаются транзакции в статусах pending (пополнение баланса)
    и client_confirmed (клиент подтвердил оплату абонемента).
    """
    
    async with get_db_context() as db:
        # Загружаем пользователей за один запрос (нет N+1)
        result = await db.execute(
            select(Transaction)
            .options(selectinload(Transaction.user))
            .where(
                Transaction.car_wash_id == user.car_wash_id,
                Transaction.status.in_(["pending", "client_confirmed"])
            )
            .order_by(Transaction.created_at.desc())
        )
        transactions = result.scalars().all()
    
    if not transactions:
        await message.answer("💰 Нет ожидающих платежей.")
        return
    
    for txn in transactions:
        client = txn.user
        status_label = "⏳ Ожидает оплаты" if txn.status == "pending" else "💳 Клиент оплатил"
        
        text = (
            f"💰 <b>Платеж #{txn.id}</b>\n\n"
            f"Клиент: {client.full_name}\n"
            f"Сумма: {txn.amount}₽\n"
            f"Тип: {txn.type}\n"
            f"Статус: {status_label}\n"
            f"Дата: {txn.created_at.strftime('%d.%m.%Y %H:%M')}"
        )
        
        await message.answer(
            text,
            reply_markup=get_payment_keyboard(txn.id)
        )

@router.callback_query(F.data.startswith("approve_pay:"))
async def approve_payment(callback: CallbackQuery, user: dict):
    """Подтверждение платежа администратором.
    Для абонементов создаёт Subscription по параметрам из txn.meta (шаблон абонемента).
    """
    txn_id = int(callback.data.split(":")[1])
    
    async with get_db_context() as db:
        result = await db.execute(
            select(Transaction).where(Transaction.id == txn_id)
        )
        txn = result.scalar_one()
        
        # Защита от повторного подтверждения
        if txn.status not in ("pending", "client_confirmed"):
            await callback.answer("Платеж уже обработан", show_alert=True)
            return
        
        txn.status = "approved"
        txn.admin_id = user.id
        txn.approved_at = datetime.now()
        
        # Начисляем абонемент или пополняем баланс
        if txn.type == "subscription_purchase":
            # Получаем параметры шаблона, сохранённые при создании транзакции
            meta = txn.meta or {}
            subscription = Subscription(
                user_id=txn.user_id,
                car_wash_id=txn.car_wash_id,
                name=meta.get("name", "Абонемент"),
                total_washes=meta.get("washes", 5),
                remaining_washes=meta.get("washes", 5),
                purchase_price=txn.amount,
                valid_until=datetime.now().date() + timedelta(days=meta.get("days", 30)),
                is_active=True
            )
            db.add(subscription)
            await db.flush()  # получаем subscription.id до commit
            txn.subscription_id = subscription.id
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

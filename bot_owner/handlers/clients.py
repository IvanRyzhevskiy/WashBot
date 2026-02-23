from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, or_

from core.database import get_db_context
from core.models import User, Appointment, Service, Subscription
from bot_owner.keyboards import get_client_actions_keyboard

router = Router()

@router.message(F.text == "👥 Клиенты")
async def list_clients(message: Message):
    """Список клиентов"""
    telegram_id = message.from_user.id
    
    async with get_db_context() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        owner = result.scalar_one()
        
        result = await db.execute(
            select(User)
            .where(
                User.car_wash_id == owner.car_wash_id,
                User.role == "client"
            )
            .order_by(User.created_at.desc())
            .limit(10)
        )
        clients = result.scalars().all()
    
    if not clients:
        await message.answer("Клиентов пока нет.")
        return
    
    text = "👥 <b>Последние клиенты:</b>\n\n"
    
    for client in clients:
        text += f"• {client.full_name}"
        if client.username:
            text += f" (@{client.username})"
        text += f"\n  Баланс: {client.balance}₽\n\n"
    
    await message.answer(text)

@router.callback_query(F.data.startswith("client_balance:"))
async def client_balance(callback: CallbackQuery):
    """Баланс клиента"""
    client_id = int(callback.data.split(":")[1])
    
    async with get_db_context() as db:
        result = await db.execute(
            select(User).where(User.id == client_id)
        )
        client = result.scalar_one()
        
        result = await db.execute(
            select(Subscription)
            .where(
                Subscription.user_id == client_id,
                Subscription.is_active == True
            )
        )
        subs = result.scalars().all()
    
    text = (
        f"👤 <b>{client.full_name}</b>\n\n"
        f"💰 Баланс: {client.balance}₽\n\n"
        f"🎫 Активные абонементы:\n"
    )
    
    if subs:
        for sub in subs:
            text += f"• {sub.name}: осталось {sub.remaining_washes}/{sub.total_washes}\n"
    else:
        text += "Нет активных абонементов"
    
    await callback.message.edit_text(text)
    await callback.answer()

@router.callback_query(F.data.startswith("client_history:"))
async def client_history(callback: CallbackQuery):
    """История клиента"""
    client_id = int(callback.data.split(":")[1])
    
    async with get_db_context() as db:
        result = await db.execute(
            select(User).where(User.id == client_id)
        )
        client = result.scalar_one()
        
        result = await db.execute(
            select(Appointment)
            .where(Appointment.user_id == client_id)
            .order_by(Appointment.appointment_time.desc())
            .limit(5)
        )
        appointments = result.scalars().all()
    
    text = f"📋 <b>История {client.full_name}</b>\n\n"
    
    if appointments:
        for apt in appointments:
            async with get_db_context() as db:
                result = await db.execute(
                    select(Service).where(Service.id == apt.service_id)
                )
                service = result.scalar_one()
            
            date_str = apt.appointment_time.strftime("%d.%m.%Y %H:%M")
            text += f"• {date_str} - {service.name} ({apt.status})\n"
    else:
        text += "Нет записей"
    
    await callback.message.edit_text(text)
    await callback.answer()

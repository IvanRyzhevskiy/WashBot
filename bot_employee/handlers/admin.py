from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, date
from sqlalchemy import select, and_

from core.database import get_db_context
from core.models import Appointment, User, Service, Transaction, Subscription
from bot_employee.keyboards import get_payment_keyboard
from bot_employee.states import TariffStates

router = Router()

CAR_CATEGORY_DISPLAY = {
    "sedan": "Седан",
    "crossover": "Кроссовер",
    "suv": "Внедорожник",
}

CAR_CATEGORY_INPUT_MAP = {
    "1": "sedan", "седан": "sedan",
    "2": "crossover", "кроссовер": "crossover",
    "3": "suv", "внедорожник": "suv",
}

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


@router.message(F.text == "🧼 Управление тарифами")
async def show_tariffs(message: Message, user: dict):
    """Показать список тарифов"""
    async with get_db_context() as db:
        result = await db.execute(
            select(Service)
            .where(Service.car_wash_id == user.car_wash_id)
            .order_by(Service.name)
        )
        services = result.scalars().all()

    if not services:
        await message.answer(
            "🧼 Тарифов пока нет.\n\nДобавить новый: /add_tariff"
        )
        return

    text = "🧼 <b>Тарифы:</b>\n\n"
    for s in services:
        status = "✅" if s.is_active else "❌"
        category = CAR_CATEGORY_DISPLAY.get(s.car_category, s.car_category)
        text += (
            f"{status} <b>{s.name}</b>\n"
            f"   Цена: {s.price}₽ | Длительность: {s.duration} мин\n"
            f"   {s.description or '—'}\n"
            f"   Категория: {category} | Макс. скидка: {s.max_discount_percent}%\n\n"
        )
    text += "Добавить новый тариф: /add_tariff"
    await message.answer(text)


@router.message(F.text == "/add_tariff")
async def add_tariff_start(message: Message, state: FSMContext):
    """Начало создания тарифа"""
    await state.set_state(TariffStates.name)
    await message.answer("Введите название тарифа:")


@router.message(TariffStates.name)
async def tariff_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым. Введите название тарифа:")
        return
    await state.update_data(name=name)
    await state.set_state(TariffStates.description)
    await message.answer("Введите описание тарифа:")


@router.message(TariffStates.description)
async def tariff_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(TariffStates.price)
    await message.answer("Введите цену (рубли, число):")


@router.message(TariffStates.price)
async def tariff_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Некорректная цена. Введите положительное число:")
        return
    await state.update_data(price=price)
    await state.set_state(TariffStates.duration)
    await message.answer("Введите длительность (минуты, целое число > 0):")


@router.message(TariffStates.duration)
async def tariff_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text.strip())
        if duration <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Некорректная длительность. Введите целое число больше 0:")
        return
    await state.update_data(duration=duration)
    await state.set_state(TariffStates.car_category)
    await message.answer("Выберите категорию автомобиля:\n1 — Седан / 2 — Кроссовер / 3 — Внедорожник")


@router.message(TariffStates.car_category)
async def tariff_car_category(message: Message, state: FSMContext):
    value = message.text.strip().lower()
    category = CAR_CATEGORY_INPUT_MAP.get(value)
    if not category:
        await message.answer(
            "Некорректный выбор. Введите:\n1 — Седан / 2 — Кроссовер / 3 — Внедорожник"
        )
        return
    await state.update_data(car_category=category)
    await state.set_state(TariffStates.max_discount)
    await message.answer("Введите максимально допустимую скидку (0–100%):")


@router.message(TariffStates.max_discount)
async def tariff_max_discount(message: Message, state: FSMContext, user: dict):
    """Финальный шаг — сохранение тарифа"""
    try:
        max_discount = int(message.text.strip())
        if not (0 <= max_discount <= 100):
            raise ValueError
    except ValueError:
        await message.answer("Некорректное значение. Введите целое число от 0 до 100:")
        return

    data = await state.get_data()
    await state.clear()

    async with get_db_context() as db:
        service = Service(
            car_wash_id=user.car_wash_id,
            name=data["name"],
            description=data["description"],
            price=data["price"],
            duration=data["duration"],
            car_category=data["car_category"],
            max_discount_percent=max_discount,
            is_active=True,
        )
        db.add(service)
        await db.commit()

    category = CAR_CATEGORY_DISPLAY.get(data["car_category"], data["car_category"])
    await message.answer(
        f"✅ <b>Тариф добавлен!</b>\n\n"
        f"Название: {data['name']}\n"
        f"Описание: {data['description']}\n"
        f"Цена: {data['price']}₽\n"
        f"Длительность: {data['duration']} мин\n"
        f"Категория: {category}\n"
        f"Макс. скидка: {max_discount}%"
    )

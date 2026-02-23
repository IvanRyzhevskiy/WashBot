from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
import qrcode
from io import BytesIO
from sqlalchemy import select

from core.database import get_db_context
from core.models import User, Transaction
from bot_client.states import SubscriptionStates
from bot_client.keyboards import get_subscriptions_keyboard, get_payment_keyboard

router = Router()

# Шаблоны абонементов
SUBSCRIPTION_TEMPLATES = [
    {"id": 1, "name": "🌱 Эконом", "washes": 5, "price": 2000, "days": 30},
    {"id": 2, "name": "🌿 Стандарт", "washes": 10, "price": 3500, "days": 45},
    {"id": 3, "name": "🌳 Премиум", "washes": 20, "price": 6000, "days": 60},
]

@router.message(F.text == "🎫 Абонементы")
async def show_subscriptions(message: Message, state: FSMContext):
    """Показать доступные абонементы"""
    await state.set_state(SubscriptionStates.choosing)
    await message.answer(
        "🎫 <b>Доступные абонементы:</b>\n\n"
        "Абонемент дает право на определенное количество моек.",
        reply_markup=get_subscriptions_keyboard(SUBSCRIPTION_TEMPLATES)
    )

@router.callback_query(SubscriptionStates.choosing, F.data.startswith("buy_sub:"))
async def buy_subscription(callback: CallbackQuery, state: FSMContext):
    """Покупка абонемента"""
    sub_id = int(callback.data.split(":")[1])
    template = next((s for s in SUBSCRIPTION_TEMPLATES if s["id"] == sub_id), None)
    
    if not template:
        await callback.answer("Абонемент не найден")
        return
    
    await state.update_data(template=template)
    
    # Создаем транзакцию
    async with get_db_context() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one()
        
        transaction = Transaction(
            user_id=user.id,
            car_wash_id=user.car_wash_id,
            amount=template["price"],
            type="subscription_purchase",
            status="pending",
            # Сохраняем шаблон, чтобы администратор мог создать абонемент с правильными параметрами
            template_id=template["id"],
            meta={
                "name": template["name"],
                "washes": template["washes"],
                "price": template["price"],
                "days": template["days"],
            },
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
    
    # Генерируем QR-код
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"WASHBOT:PAY:{template['price']}:{template['name']}")
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    
    await callback.message.delete()
    await callback.message.answer_photo(
        BufferedInputFile(bio.getvalue(), filename="qr.png"),
        caption=(
            f"💳 <b>Оплата абонемента</b>\n\n"
            f"{template['name']}\n"
            f"Сумма: {template['price']}₽\n\n"
            f"1️⃣ Оплатите по QR-коду\n"
            f"2️⃣ Нажмите 'Я оплатил'\n"
            f"3️⃣ Администратор подтвердит платеж"
        ),
        reply_markup=get_payment_keyboard(transaction.id)
    )
    
    await state.set_state(SubscriptionStates.waiting_payment)
    await callback.answer()

@router.callback_query(SubscriptionStates.waiting_payment, F.data.startswith("paid:"))
async def payment_confirmed(callback: CallbackQuery, state: FSMContext):
    """Подтверждение оплаты клиентом — переводим транзакцию в статус client_confirmed.
    Администратор проверит платёж и создаст абонемент."""
    transaction_id = int(callback.data.split(":")[1])
    
    async with get_db_context() as db:
        result = await db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        transaction = result.scalar_one()
        
        if transaction.status != "pending":
            await callback.message.edit_text("❌ Транзакция уже обработана")
            await state.clear()
            await callback.answer()
            return
        
        # Клиент подтверждает, что оплатил — ждём подтверждения администратора
        transaction.status = "client_confirmed"
        await db.commit()
    
    data = await state.get_data()
    template = data.get("template", {})
    
    await callback.message.edit_text(
        f"⏳ <b>Платёж отправлен на проверку</b>\n\n"
        f"{template.get('name', 'Абонемент')}\n"
        f"Сумма: {template.get('price', '')}₽\n\n"
        f"Администратор проверит оплату и активирует абонемент."
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    """Отмена оплаты"""
    await state.clear()
    await callback.message.edit_text("❌ Оплата отменена.")
    await callback.answer()

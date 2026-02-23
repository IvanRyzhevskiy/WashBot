from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from datetime import datetime, timedelta
from typing import List, Dict

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню клиента"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🚗 Записаться"),
        KeyboardButton(text="🎫 Абонементы")
    )
    builder.row(
        KeyboardButton(text="⭐ Мои записи"),
        KeyboardButton(text="📞 Контакты")
    )
    return builder.as_markup(resize_keyboard=True)

def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для запроса телефона"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📱 Отправить номер", request_contact=True))
    builder.add(KeyboardButton(text="◀️ Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def get_services_keyboard(services: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора услуг"""
    builder = InlineKeyboardBuilder()
    for s in services:
        builder.row(
            InlineKeyboardButton(
                text=f"{s['name']} - {s['price']}₽ ({s['duration']} мин)",
                callback_data=f"service:{s['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    return builder.as_markup()

def get_dates_keyboard(days: int = 7) -> InlineKeyboardMarkup:
    """Клавиатура выбора даты"""
    builder = InlineKeyboardBuilder()
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    for i in range(days):
        date = datetime.now() + timedelta(days=i)
        weekday = weekdays[date.weekday()]
        date_str = date.strftime(f"%d.%m")
        callback = date.strftime("%Y-%m-%d")
        builder.row(
            InlineKeyboardButton(
                text=f"{date_str} ({weekday})",
                callback_data=f"date:{callback}"
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_services"))
    return builder.as_markup()

def get_times_keyboard(times: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени"""
    builder = InlineKeyboardBuilder()
    for time in times:
        builder.add(InlineKeyboardButton(text=time, callback_data=f"time:{time}"))
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_dates"))
    return builder.as_markup()

def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()

def get_subscriptions_keyboard(subs: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура абонементов"""
    builder = InlineKeyboardBuilder()
    for s in subs:
        builder.row(
            InlineKeyboardButton(
                text=f"{s['name']} - {s['price']}₽",
                callback_data=f"buy_sub:{s['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    return builder.as_markup()

def get_payment_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    """Клавиатура оплаты"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💳 Я оплатил",
            callback_data=f"paid:{transaction_id}"
        )
    )
    builder.row(InlineKeyboardButton(text="◀️ Отмена", callback_data="cancel_payment"))
    return builder.as_markup()

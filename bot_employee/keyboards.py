from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура администратора"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📝 Записать клиента"))
    builder.row(KeyboardButton(text="📅 Посмотреть записи"))
    builder.row(KeyboardButton(text="🧼 Управление тарифами"))
    return builder.as_markup(resize_keyboard=True)

def get_washer_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура мойщика"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🚗 Мои записи"),
        KeyboardButton(text="✅ Отметить выполнение")
    )
    builder.row(
        KeyboardButton(text="📊 Моя статистика")
    )
    return builder.as_markup(resize_keyboard=True)

def get_payment_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    """Кнопки для подтверждения платежа"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"approve_pay:{transaction_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"reject_pay:{transaction_id}"
        )
    )
    return builder.as_markup()

def get_appointment_complete_keyboard(appointment_id: int) -> InlineKeyboardMarkup:
    """Кнопка отметки выполнения"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Выполнено",
        callback_data=f"complete:{appointment_id}"
    ))
    return builder.as_markup()

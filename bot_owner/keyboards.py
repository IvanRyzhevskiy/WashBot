from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню владельца"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📊 Дашборд"),
        KeyboardButton(text="👥 Клиенты")
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="📈 Отчеты")
    )
    return builder.as_markup(resize_keyboard=True)

def get_client_actions_keyboard(client_id: int) -> InlineKeyboardMarkup:
    """Действия с клиентом"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💰 Баланс",
            callback_data=f"client_balance:{client_id}"
        ),
        InlineKeyboardButton(
            text="📋 История",
            callback_data=f"client_history:{client_id}"
        )
    )
    return builder.as_markup()

def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Настройки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🧼 Услуги", callback_data="settings_services"),
        InlineKeyboardButton(text="🕐 График", callback_data="settings_schedule")
    )
    builder.row(
        InlineKeyboardButton(text="🎫 Абонементы", callback_data="settings_subs"),
        InlineKeyboardButton(text="👥 Сотрудники", callback_data="settings_staff")
    )
    return builder.as_markup()

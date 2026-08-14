from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo
)
from bot.config import config

def format_price(amount: int) -> str:
    """Formats amount like 25000 -> 25 000 сум."""
    formatted_num = f"{amount:,}".replace(",", " ")
    return f"{formatted_num} {config.CURRENCY_SYMBOL}"

def get_main_menu(is_subscribed: bool = False, webapp_url: str = "", is_admin: bool = False) -> ReplyKeyboardMarkup:
    url = webapp_url or config.CINEMA_URL
    
    keyboard = []
    if is_subscribed:
        keyboard.append([
            KeyboardButton(
                text="🎬 Открыть кинотеатр",
                web_app=WebAppInfo(url=url)
            )
        ])
        keyboard.append([
            KeyboardButton(text="👤 Мой профиль"),
            KeyboardButton(text="💎 Продлить подписку")
        ])
        keyboard.append([
            KeyboardButton(text="ℹ️ Помощь / Поддержка")
        ])
    else:
        keyboard.append([
            KeyboardButton(text="💳 Купить доступ в кинотеатр")
        ])
        keyboard.append([
            KeyboardButton(text="👤 Мой профиль"),
            KeyboardButton(text="ℹ️ О кинотеатре")
        ])

    if is_admin:
        keyboard.append([
            KeyboardButton(text="👑 Админ-панель")
        ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True
    )

def get_payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Я оплатил (Отправить чек)",
                    callback_data="start_payment_upload"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel_action"
                )
            ]
        ]
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_admin_payment_keyboard(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить 30 дней",
                    callback_data=f"admin_approve:{req_id}:30"
                ),
                InlineKeyboardButton(
                    text="✅ Одобрить 90 дней",
                    callback_data=f"admin_approve:{req_id}:90"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить платёж",
                    callback_data=f"admin_reject:{req_id}"
                )
            ]
        ]
    )

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="➕ Выдать VIP", callback_data="admin_grant_start")
            ],
            [
                InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast_start"),
                InlineKeyboardButton(text="💳 Реквизиты и цена", callback_data="admin_view_pricing")
            ],
            [
                InlineKeyboardButton(text="❌ Закрыть панель", callback_data="admin_close_panel")
            ]
        ]
    )

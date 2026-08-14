from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timezone

from bot.config import config
from bot.database import db
from bot.keyboards import (
    get_main_menu,
    get_admin_panel_keyboard,
    format_price
)

router = Router()

class AdminStates(StatesGroup):
    waiting_for_grant_data = State()
    waiting_for_broadcast_text = State()

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

async def build_admin_dashboard_text() -> str:
    stats = await db.get_stats()
    revenue_text = format_price(stats['total_revenue'])
    price_text = format_price(config.SUBSCRIPTION_PRICE)
    
    db_type = "🐘 <b>PostgreSQL (Cloud - данные сохраняются навсегда)</b> ✅" if db.is_postgres else "📁 <b>SQLite (Локальная)</b> ⚠️"
    
    return (
        "👑 <b>Панель управления администратора</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"• Активных VIP-подписчиков: <b>{stats['active_subs']}</b>\n"
        f"• Ожидает проверки оплат: <b>{stats['pending_payments']}</b>\n"
        f"• Общая выручка: <b>{revenue_text}</b>\n\n"
        f"💳 <b>Настройки:</b>\n"
        f"• Тариф: <b>{price_text} / {config.SUBSCRIPTION_DAYS} дней</b>\n"
        f"• Банк/Карта: <b>{config.CARD_BANK}</b> (<code>{config.CARD_NUMBER}</code>)\n"
        f"• База данных: {db_type}\n\n"
        "<i>Используйте кнопки ниже для быстрого управления:</i>"
    )

@router.message(F.text == "👑 Админ-панель")
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    await state.clear()
    text = await build_admin_dashboard_text()
    await message.answer(text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав.", show_alert=True)
        return
        
    text = await build_admin_dashboard_text()
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("Статистика обновлена!")

@router.callback_query(F.data == "admin_close_panel")
async def callback_admin_close(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data == "admin_view_pricing")
async def callback_admin_pricing(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    price_text = format_price(config.SUBSCRIPTION_PRICE)
    text = (
        "💳 <b>Информация о реквизитах и тарифах</b>\n\n"
        f"💰 Стоимость подписки: <b>{price_text}</b>\n"
        f"⏳ Длительность: <b>{config.SUBSCRIPTION_DAYS} дней</b>\n"
        f"🏦 Тип карты / Банк: <b>{config.CARD_BANK}</b>\n"
        f"💳 Номер карты: <code>{config.CARD_NUMBER}</code>\n"
        f"👤 Получатель: <b>{config.CARD_HOLDER}</b>\n"
        f"🎬 Ссылка кинотеатра: <code>{config.CINEMA_URL}</code>\n\n"
        "<i>(Чтобы изменить эти данные, укажите их в переменных окружения на Render.com)</i>"
    )
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в панель", callback_data="admin_stats")]
    ])
    await callback.message.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_grant_start")
async def callback_grant_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав.", show_alert=True)
        return
        
    await state.set_state(AdminStates.waiting_for_grant_data)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_stats")]
    ])
    await callback.message.edit_text(
        "➕ <b>Выдача VIP-доступа вручную</b>\n\n"
        "Отправьте <b>ID пользователя</b> и (опционально) <b>количество дней</b> через пробел.\n\n"
        "<i>Пример:</i> <code>123456789 30</code>\n"
        "<i>(Если указать только ID, доступ будет выдан на 30 дней)</i>",
        reply_markup=cancel_kb,
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_grant_data)
async def process_grant_data(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
        
    parts = message.text.split()
    if not parts or not parts[0].isdigit():
        await message.answer("⚠️ Пожалуйста, введите корректный цифровой User ID. Пример: <code>123456789 30</code>", parse_mode="HTML")
        return
        
    target_user_id = int(parts[0])
    days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 30
    
    new_until = await db.grant_manual_subscription(target_user_id, days=days)
    until_formatted = new_until.strftime("%d.%m.%Y %H:%M")
    await state.clear()
    
    await message.answer(
        f"✅ Пользователю <code>{target_user_id}</code> успешно выдан VIP-доступ на <b>{days} дней</b> (до {until_formatted}).",
        reply_markup=get_main_menu(is_subscribed=True, webapp_url=config.CINEMA_URL, is_admin=True),
        parse_mode="HTML"
    )
    
    # Notify target user
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=(
                f"🎁 <b>Вам предоставлен VIP-доступ к онлайн-кинотеатру на {days} дней!</b>\n"
                f"📅 Подписка активна до: <b>{until_formatted}</b>\n\n"
                "Нажмите <b>«🎬 Открыть кинотеатр»</b> внизу экрана, чтобы начать просмотр."
            ),
            reply_markup=get_main_menu(is_subscribed=True, webapp_url=config.CINEMA_URL, is_admin=is_admin(target_user_id)),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"⚠️ Уведомление пользователю не отправлено (возможно, бот не был запущен пользователем): {e}")

@router.callback_query(F.data == "admin_broadcast_start")
async def callback_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав.", show_alert=True)
        return
        
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_stats")]
    ])
    await callback.message.edit_text(
        "📢 <b>Рассылка сообщения всем пользователям бота</b>\n\n"
        "Отправьте текст сообщения, которое получат все пользователи бота.\n"
        "<i>(Поддерживается HTML-разметка)</i>",
        reply_markup=cancel_kb,
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast_text)
async def process_broadcast_text(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
        
    text_to_send = message.text
    await state.clear()
    
    users = await db.get_all_users()
    status_msg = await message.answer(f"⏳ Начинаю рассылку для {len(users)} пользователей...")
    
    sent_count = 0
    fail_count = 0
    
    for u in users:
        uid = u["user_id"]
        try:
            is_sub = await db.is_user_subscribed(uid)
            admin_flag = is_admin(uid)
            await bot.send_message(
                chat_id=uid,
                text=text_to_send,
                reply_markup=get_main_menu(is_sub, config.CINEMA_URL, is_admin=admin_flag),
                parse_mode="HTML"
            )
            sent_count += 1
        except Exception:
            fail_count += 1
            
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"• Успешно доставлено: <b>{sent_count}</b>\n"
        f"• Ошибок (заблокировали бота): <b>{fail_count}</b>",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_approve:"))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return
        
    parts = callback.data.split(":")
    req_id = int(parts[1])
    days = int(parts[2]) if len(parts) > 2 else 30
    
    result = await db.approve_payment_request(req_id, days=days)
    if not result:
        await callback.answer("Заявка уже обработана или не найдена!", show_alert=True)
        return
        
    user_id = result["user_id"]
    new_until = result["new_subscription_until"]
    
    # Notify user
    try:
        until_formatted = new_until.strftime("%d.%m.%Y %H:%M")
        user_msg = (
            "🎉 <b>Поздравляем! Ваш платёж успешно подтверждён!</b>\n\n"
            f"⭐ Вам активирован полный VIP-доступ на <b>{days} дней</b> (до <b>{until_formatted}</b>).\n\n"
            "Нажмите кнопку <b>«🎬 Открыть кинотеатр»</b> внизу экрана, чтобы перейти к выбору и просмотру фильмов. Приятного отдыха!"
        )
        await bot.send_message(
            chat_id=user_id,
            text=user_msg,
            reply_markup=get_main_menu(is_subscribed=True, webapp_url=config.CINEMA_URL, is_admin=is_admin(user_id)),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Failed to notify user {user_id}: {e}")

    # Edit admin message
    admin_name = callback.from_user.full_name
    curr_caption = callback.message.caption or ""
    new_caption = curr_caption + f"\n\n✅ <b>ОДОБРЕНО</b> (+{days} дн.) админом {admin_name}"
    
    try:
        await callback.message.edit_caption(
            caption=new_caption,
            reply_markup=None,
            parse_mode="HTML"
        )
    except Exception:
        pass
        
    await callback.answer(f"Платёж #{req_id} одобрен на {days} дней!")

@router.callback_query(F.data.startswith("admin_reject:"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return
        
    parts = callback.data.split(":")
    req_id = int(parts[1])
    
    user_id = await db.reject_payment_request(req_id)
    if not user_id:
        await callback.answer("Заявка уже обработана или не найдена!", show_alert=True)
        return
        
    # Notify user
    try:
        user_msg = (
            f"❌ <b>Ваша заявка на оплату #{req_id} была отклонена.</b>\n\n"
            "Возможные причины:\n"
            "• Средства не поступили на счёт\n"
            "• Некорректный или нечитаемый скриншот чека\n"
            "• Сумма перевода не совпадает с указанной\n\n"
            "Если произошла ошибка или вы уже перевели деньги, пожалуйста, отправьте корректный чек заново или свяжитесь с поддержкой."
        )
        is_sub = await db.is_user_subscribed(user_id)
        await bot.send_message(
            chat_id=user_id,
            text=user_msg,
            reply_markup=get_main_menu(is_sub, config.CINEMA_URL, is_admin=is_admin(user_id)),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Failed to notify user {user_id}: {e}")

    # Edit admin message
    admin_name = callback.from_user.full_name
    curr_caption = callback.message.caption or ""
    new_caption = curr_caption + f"\n\n❌ <b>ОТКЛОНЕНО</b> админом {admin_name}"
    
    try:
        await callback.message.edit_caption(
            caption=new_caption,
            reply_markup=None,
            parse_mode="HTML"
        )
    except Exception:
        pass
        
    await callback.answer(f"Платёж #{req_id} отклонён.")

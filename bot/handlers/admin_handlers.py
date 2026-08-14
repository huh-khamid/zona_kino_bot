from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from datetime import datetime, timezone

from bot.config import config
from bot.database import Database
from bot.keyboards import (
    get_main_menu,
    get_admin_panel_keyboard
)

router = Router()
db = Database(config.DATABASE_PATH)

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return
        
    stats = await db.get_stats()
    text = (
        "👑 <b>Панель администратора</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"⭐ Активных VIP-подписчиков: <b>{stats['active_subs']}</b>\n"
        f"⏳ Ожидает проверки оплат: <b>{stats['pending_payments']}</b>\n"
        f"💰 Общая выручка: <b>{stats['total_revenue']} ₽</b>\n\n"
        "<b>Команды управления:</b>\n"
        "• <code>/give &lt;user_id&gt; &lt;дни&gt;</code> — выдать подписку вручную (например: <code>/give 123456789 30</code>)\n"
        "• <code>/broadcast &lt;текст&gt;</code> — сделать рассылку всем пользователям бота"
    )
    await message.answer(text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав.", show_alert=True)
        return
        
    stats = await db.get_stats()
    text = (
        "👑 <b>Панель администратора (Обновлено)</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"⭐ Активных VIP-подписчиков: <b>{stats['active_subs']}</b>\n"
        f"⏳ Ожидает проверки оплат: <b>{stats['pending_payments']}</b>\n"
        f"💰 Общая выручка: <b>{stats['total_revenue']} ₽</b>\n\n"
        "<b>Команды управления:</b>\n"
        "• <code>/give &lt;user_id&gt; &lt;дни&gt;</code> — выдать подписку вручную\n"
        "• <code>/broadcast &lt;текст&gt;</code> — сделать рассылку"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("Статистика обновлена!")

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
            reply_markup=get_main_menu(is_subscribed=True, webapp_url=config.WEBAPP_URL),
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
            reply_markup=get_main_menu(is_sub, config.WEBAPP_URL),
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

@router.message(Command("give"))
async def cmd_give_access(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
        
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: <code>/give &lt;user_id&gt; [дни, по умолчанию 30]</code>", parse_mode="HTML")
        return
        
    try:
        target_user_id = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else 30
    except ValueError:
        await message.answer("Ошибка: ID пользователя и дни должны быть числами.")
        return
        
    new_until = await db.grant_manual_subscription(target_user_id, days=days)
    until_formatted = new_until.strftime("%d.%m.%Y %H:%M")
    
    await message.answer(
        f"✅ Пользователю <code>{target_user_id}</code> успешно выдана подписка на <b>{days} дней</b> (до {until_formatted}).",
        parse_mode="HTML"
    )
    
    # Notify target user
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=(
                f"🎁 <b>Вам предоставлен VIP-доступ к онлайн-кинотеатру на {days} дней!</b>\n"
                f"📅 Подписка активна до: <b>{until_formatted}</b>\n\n"
                "Нажмите <b>«🎬 Открыть кинотеатр»</b>, чтобы начать просмотр."
            ),
            reply_markup=get_main_menu(is_subscribed=True, webapp_url=config.WEBAPP_URL),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"⚠️ Не удалось отправить уведомление пользователю: {e}")

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
        
    text_to_send = message.text.replace("/broadcast", "", 1).strip()
    if not text_to_send:
        await message.answer("Укажите текст рассылки: <code>/broadcast Ваш текст здесь</code>", parse_mode="HTML")
        return
        
    async with await db.get_connection() as conn:
        async with conn.execute("SELECT user_id, status, subscription_until FROM users") as cursor:
            users = await cursor.fetchall()
            
    sent_count = 0
    fail_count = 0
    
    status_msg = await message.answer(f"⏳ Начинаю рассылку для {len(users)} пользователей...")
    
    for row in users:
        uid = row["user_id"]
        try:
            is_sub = await db.is_user_subscribed(uid)
            await bot.send_message(
                chat_id=uid,
                text=text_to_send,
                reply_markup=get_main_menu(is_sub, config.WEBAPP_URL),
                parse_mode="HTML"
            )
            sent_count += 1
        except Exception:
            fail_count += 1
            
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"• Успешно доставлено: <b>{sent_count}</b>\n"
        f"• Ошибок / заблокировали бота: <b>{fail_count}</b>",
        parse_mode="HTML"
    )

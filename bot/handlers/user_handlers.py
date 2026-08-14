from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timezone

from bot.config import config
from bot.database import db
from bot.keyboards import (
    get_main_menu,
    get_payment_keyboard,
    get_cancel_keyboard,
    get_admin_payment_keyboard,
    format_price
)

router = Router()

class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    user = await db.get_or_create_user(
        user_id=user_id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    is_sub = await db.is_user_subscribed(user_id)
    admin_flag = is_admin(user_id)
    
    welcome_text = (
        f"👋 <b>Добро пожаловать в Онлайн-Кинотеатр, {message.from_user.first_name}!</b>\n\n"
        "🍿 Здесь вы найдете огромную библиотеку новинок кино, сериалов, мультфильмов и аниме в отличном качестве (1080p / 4K) с выбором озвучек.\n\n"
    )
    
    if is_sub:
        welcome_text += (
            "✅ <b>У вас активна VIP-подписка!</b>\n"
            "Нажмите кнопку <b>«🎬 Открыть кинотеатр»</b> внизу экрана, чтобы перейти к просмотру."
        )
    else:
        price_text = format_price(config.SUBSCRIPTION_PRICE)
        welcome_text += (
            f"🔒 <b>Для доступа к плееру и просмотру фильмов необходима подписка.</b>\n"
            f"💰 Стоимость: <b>{price_text} / {config.SUBSCRIPTION_DAYS} дней</b>.\n\n"
            "Нажмите <b>«💳 Купить доступ в кинотеатр»</b>, чтобы оформить подписку."
        )
        
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu(is_sub, config.CINEMA_URL, is_admin=admin_flag),
        parse_mode="HTML"
    )

@router.message(F.text.in_(["💳 Купить доступ в кинотеатр", "💎 Продлить подписку"]))
async def show_payment_info(message: Message, state: FSMContext):
    await state.clear()
    is_sub = await db.is_user_subscribed(message.from_user.id)
    action_text = "Продление подписки" if is_sub else "Оформление подписки"
    price_text = format_price(config.SUBSCRIPTION_PRICE)
    
    payment_info = (
        f"💳 <b>{action_text}</b>\n\n"
        f"💰 Сумма к оплате: <b>{price_text}</b>\n"
        f"⏳ Срок действия: <b>{config.SUBSCRIPTION_DAYS} дней</b>\n\n"
        "<b>Реквизиты для перевода:</b>\n"
        f"🏦 Тип карты / Банк: <b>{config.CARD_BANK}</b>\n"
        f"💳 Номер карты: <code>{config.CARD_NUMBER}</code> <i>(нажмите, чтобы скопировать)</i>\n"
        f"👤 Получатель: <b>{config.CARD_HOLDER}</b>\n\n"
        "<b>Инструкция:</b>\n"
        "1. Переведите точную сумму на указанную карту.\n"
        "2. Нажмите кнопку <b>«📤 Я оплатил (Отправить чек)»</b> ниже.\n"
        "3. Пришлите боту скриншот квитанции/чека об успешном переводе.\n"
        "4. После быстрой проверки бот автоматически откроет вам доступ к кинотеатру!"
    )
    
    await message.answer(
        payment_info,
        reply_markup=get_payment_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "start_payment_upload")
async def start_payment_upload(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PaymentStates.waiting_for_receipt)
    await callback.message.edit_text(
        "📸 <b>Пожалуйста, отправьте скриншот или PDF-файл чека об оплате</b> в ответ на это сообщение.\n\n"
        "<i>Убедитесь, что на чеке видны дата, время и сумма перевода.</i>",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Вы можете отменить отправку кнопкой ниже:",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_action")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = callback.from_user.id
    is_sub = await db.is_user_subscribed(uid)
    admin_flag = is_admin(uid)
    await callback.message.delete()
    await callback.message.answer(
        "Действие отменено.",
        reply_markup=get_main_menu(is_sub, config.CINEMA_URL, is_admin=admin_flag)
    )
    await callback.answer()

@router.message(F.text == "❌ Отменить")
async def cancel_text(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    is_sub = await db.is_user_subscribed(uid)
    admin_flag = is_admin(uid)
    await message.answer(
        "Действие отменено.",
        reply_markup=get_main_menu(is_sub, config.CINEMA_URL, is_admin=admin_flag)
    )

@router.message(PaymentStates.waiting_for_receipt, F.content_type.in_([ContentType.PHOTO, ContentType.DOCUMENT]))
async def process_receipt(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    admin_flag = is_admin(user_id)
    
    if message.photo:
        file_id = message.photo[-1].file_id
        is_photo = True
    elif message.document:
        file_id = message.document.file_id
        is_photo = False
    else:
        await message.answer("Пожалуйста, отправьте фото чека или документ.")
        return

    # Create request in DB
    req_id = await db.create_payment_request(
        user_id=user_id,
        username=username,
        full_name=full_name,
        amount=config.SUBSCRIPTION_PRICE,
        receipt_file_id=file_id
    )
    
    await state.clear()
    
    is_sub = await db.is_user_subscribed(user_id)
    await message.answer(
        "✅ <b>Ваш чек успешно принят в обработку!</b>\n\n"
        f"Заявка <b>#{req_id}</b> отправлена администратору на проверку.\n"
        "Обычно подтверждение занимает от 2 до 15 минут. Как только оплата будет зачислена, вам придет уведомление!",
        reply_markup=get_main_menu(is_sub, config.CINEMA_URL, is_admin=admin_flag),
        parse_mode="HTML"
    )
    
    # Notify Admins
    price_text = format_price(config.SUBSCRIPTION_PRICE)
    admin_caption = (
        f"🔔 <b>Новая заявка на оплату #{req_id}</b>\n\n"
        f"👤 <b>Пользователь:</b> {full_name} ({f'@{username}' if username else 'без юзернейма'})\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"💰 <b>Сумма:</b> {price_text}\n"
        f"📅 <b>Время:</b> {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}"
    )
    
    admin_kb = get_admin_payment_keyboard(req_id)
    
    for admin_id in config.ADMIN_IDS:
        try:
            if is_photo:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=file_id,
                    caption=admin_caption,
                    reply_markup=admin_kb,
                    parse_mode="HTML"
                )
            else:
                await bot.send_document(
                    chat_id=admin_id,
                    document=file_id,
                    caption=admin_caption,
                    reply_markup=admin_kb,
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"Error sending receipt to admin {admin_id}: {e}")

@router.message(PaymentStates.waiting_for_receipt)
async def invalid_receipt_message(message: Message):
    await message.answer(
        "⚠️ Пожалуйста, отправьте именно <b>фотографию (скриншот) или документ</b> с чеком.",
        parse_mode="HTML"
    )

@router.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    is_sub = await db.is_user_subscribed(user_id)
    admin_flag = is_admin(user_id)
    
    if not user:
        user = await db.get_or_create_user(user_id, message.from_user.username, message.from_user.full_name)
    
    profile_text = (
        f"👤 <b>Личный кабинет</b>\n\n"
        f"🆔 Ваш ID: <code>{user_id}</code>\n"
        f"🏷 Имя: <b>{message.from_user.full_name}</b>\n"
    )
    
    if is_sub and user.get("subscription_until"):
        sub_raw = user["subscription_until"]
        sub_dt = datetime.fromisoformat(sub_raw) if isinstance(sub_raw, str) else sub_raw
        now_dt = datetime.now(timezone.utc)
        if sub_dt.tzinfo is None:
            sub_dt = sub_dt.replace(tzinfo=timezone.utc)
            
        remaining_days = max(0, (sub_dt - now_dt).days)
        profile_text += (
            f"⭐ Статус подписки: <b>VIP Активна</b> ✅\n"
            f"📅 Действует до: <b>{sub_dt.strftime('%d.%m.%Y %H:%M')}</b>\n"
            f"⏳ Осталось: <b>{remaining_days} дн.</b>"
        )
    else:
        profile_text += (
            "⭐ Статус подписки: <b>Не активна</b> ❌\n\n"
            "Оформите подписку, чтобы получить неограниченный доступ ко всем фильмам и сериалам без рекламы!"
        )
        
    await message.answer(
        profile_text,
        reply_markup=get_main_menu(is_sub, config.CINEMA_URL, is_admin=admin_flag),
        parse_mode="HTML"
    )

@router.message(F.text.in_(["ℹ️ О кинотеатре", "ℹ️ Помощь / Поддержка"]))
async def show_info(message: Message):
    uid = message.from_user.id
    is_sub = await db.is_user_subscribed(uid)
    admin_flag = is_admin(uid)
    info_text = (
        "🍿 <b>О нашем онлайн-кинотеатре</b>\n\n"
        "✨ <b>Что входит в подписку:</b>\n"
        "• Более 100 000+ фильмов, сериалов, мультфильмов и аниме\n"
        "• Высокое качество видео (Full HD 1080p, 4K HDR)\n"
        "• Выбор любимой русской озвучки (LostFilm, HDRezka, Дубляж и др.)\n"
        "• Удобный поиск по названию, жанрам и годам\n"
        "• Быстрый запуск прямо внутри Telegram на смартфонах и ПК\n"
        "• Без рекламы и задержек\n\n"
        "💬 <b>Поддержка:</b>\n"
        "Если у вас возникли вопросы по оплате или доступу, напишите администратору."
    )
    await message.answer(
        info_text,
        reply_markup=get_main_menu(is_sub, config.CINEMA_URL, is_admin=admin_flag),
        parse_mode="HTML"
    )

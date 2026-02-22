"""
Telegram-бот для салона красоты
================================
Демо-проект для портфолио.

Функции:
- Каталог услуг по категориям (с фото и ценами)
- Наши мастера (кто работает)
- Онлайн-запись на услугу (имя, услуга, дата, время)
- Акции и спецпредложения
- Информация о салоне (адрес, часы работы, контакты)
- Отзывы / обратная связь

Для запуска:
1. pip install python-telegram-bot
2. Получить токен у @BotFather в Telegram
3. Вставить токен в config.py
4. python bot.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

from config import BOT_TOKEN, SALON_INFO, SERVICES, MASTERS, PROMOS, ADMIN_CHAT_ID

# --- Логирование ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Состояния для записи ---
APPT_NAME, APPT_SERVICE, APPT_DATE, APPT_TIME = range(4)


# ==============================
#  ГЛАВНОЕ МЕНЮ
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и главное меню."""
    keyboard = [
        [InlineKeyboardButton("Услуги и цены", callback_data="services")],
        [InlineKeyboardButton("Наши мастера", callback_data="masters")],
        [InlineKeyboardButton("Записаться", callback_data="appointment")],
        [InlineKeyboardButton("Акции", callback_data="promos")],
        [InlineKeyboardButton("О салоне", callback_data="about")],
        [InlineKeyboardButton("Оставить отзыв", callback_data="feedback")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome = (
        f"Добро пожаловать в {SALON_INFO['name']}!\n\n"
        "Выберите, что вас интересует:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(welcome, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome, reply_markup=reply_markup)


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка 'Назад' — возврат в главное меню."""
    await start(update, context)


# ==============================
#  УСЛУГИ
# ==============================

async def show_service_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать категории услуг."""
    query = update.callback_query
    await query.answer()

    keyboard = []
    for category in SERVICES:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"svc_{category}")])
    keyboard.append([InlineKeyboardButton("< Назад", callback_data="main")])

    await query.edit_message_text(
        "Выберите категорию услуг:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_service_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать услуги из выбранной категории с фотографиями."""
    query = update.callback_query
    await query.answer()

    category = query.data.replace("svc_", "")
    items = SERVICES.get(category, [])

    # Удаляем старое сообщение
    try:
        await query.message.delete()
    except Exception:
        pass

    # Отправляем каждую услугу с фотографией
    for item in items:
        caption = f"{item['name']}\n{item['price']} руб. | {item['time']}"

        photo_url = item.get("photo")
        if photo_url:
            try:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=photo_url,
                    caption=caption,
                )
            except Exception:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=caption,
                )
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=caption,
            )

    # Кнопки навигации
    keyboard = [
        [InlineKeyboardButton("Записаться", callback_data="appointment")],
        [InlineKeyboardButton("< К категориям", callback_data="services")],
        [InlineKeyboardButton("<< Главное меню", callback_data="main")],
    ]
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"{category} — выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ==============================
#  МАСТЕРА
# ==============================

async def show_masters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список мастеров."""
    query = update.callback_query
    await query.answer()

    text = "Наши мастера:\n\n"
    for m in MASTERS:
        text += f"  {m['name']} — {m['role']}\n  {m['exp']}\n\n"

    keyboard = [
        [InlineKeyboardButton("Записаться", callback_data="appointment")],
        [InlineKeyboardButton("< Назад", callback_data="main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# ==============================
#  ЗАПИСЬ НА УСЛУГУ
# ==============================

async def appointment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало записи — запрос имени."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Давайте запишем вас!\n\n"
        "Введите ваше имя:"
    )
    return APPT_NAME


async def appointment_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получили имя, показываем список услуг для выбора."""
    context.user_data["appt_name"] = update.message.text

    # Собираем все услуги в плоский список
    all_services = []
    for cat, items in SERVICES.items():
        for item in items:
            all_services.append(f"{item['name']} ({item['price']} руб.)")

    text = f"Отлично, {update.message.text}!\n\nКакую услугу хотите?\n\n"
    for i, svc in enumerate(all_services, 1):
        text += f"{i}. {svc}\n"
    text += "\nВведите номер или название услуги:"

    # Сохраняем список для маппинга
    context.user_data["service_list"] = all_services

    await update.message.reply_text(text)
    return APPT_SERVICE


async def appointment_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получили услугу, запрашиваем дату."""
    user_input = update.message.text.strip()
    service_list = context.user_data.get("service_list", [])

    # Если ввели номер
    if user_input.isdigit():
        idx = int(user_input) - 1
        if 0 <= idx < len(service_list):
            context.user_data["appt_service"] = service_list[idx]
        else:
            context.user_data["appt_service"] = user_input
    else:
        context.user_data["appt_service"] = user_input

    await update.message.reply_text(
        f"Услуга: {context.user_data['appt_service']}\n\n"
        "На какую дату записать? (например: 25.02.2026)"
    )
    return APPT_DATE


async def appointment_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получили дату, запрашиваем время."""
    context.user_data["appt_date"] = update.message.text
    await update.message.reply_text(
        "На какое время? (например: 14:00)\n\n"
        "Мы работаем с 09:00 до 21:00"
    )
    return APPT_TIME


async def appointment_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получили всё — подтверждаем запись."""
    context.user_data["appt_time"] = update.message.text
    data = context.user_data

    confirmation = (
        "Ваша запись:\n\n"
        f"  Имя: {data['appt_name']}\n"
        f"  Услуга: {data['appt_service']}\n"
        f"  Дата: {data['appt_date']}\n"
        f"  Время: {data['appt_time']}\n\n"
        "Мы свяжемся с вами для подтверждения.\n"
        f"Или позвоните нам: {SALON_INFO['phone']}\n\n"
        "Ждём вас!"
    )

    keyboard = [[InlineKeyboardButton("На главную", callback_data="main")]]
    await update.message.reply_text(confirmation, reply_markup=InlineKeyboardMarkup(keyboard))

    # Отправляем уведомление администратору
    user = update.effective_user
    admin_msg = (
        "🔔 Новая запись!\n\n"
        f"Имя: {data['appt_name']}\n"
        f"Услуга: {data['appt_service']}\n"
        f"Дата: {data['appt_date']}\n"
        f"Время: {data['appt_time']}\n\n"
        f"Клиент: {user.full_name}"
    )
    if user.username:
        admin_msg += f" (@{user.username})"
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)

    return ConversationHandler.END


async def appointment_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена записи."""
    await update.message.reply_text("Запись отменена.")
    return ConversationHandler.END


# ==============================
#  АКЦИИ
# ==============================

async def show_promos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущие акции."""
    query = update.callback_query
    await query.answer()

    if not PROMOS:
        text = "Сейчас акций нет, но скоро появятся!"
    else:
        text = "Наши акции:\n\n"
        for promo in PROMOS:
            text += f"  {promo['title']}\n  {promo['desc']}\n\n"

    keyboard = [
        [InlineKeyboardButton("Записаться", callback_data="appointment")],
        [InlineKeyboardButton("< Назад", callback_data="main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# ==============================
#  О САЛОНЕ
# ==============================

async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о салоне."""
    query = update.callback_query
    await query.answer()

    info = SALON_INFO
    text = (
        f"{info['name']}\n\n"
        f"  Адрес: {info['address']}\n"
        f"  Телефон: {info['phone']}\n"
        f"  Часы работы: {info['hours']}\n\n"
        f"{info['description']}"
    )

    keyboard = [
        [InlineKeyboardButton("Записаться", callback_data="appointment")],
        [InlineKeyboardButton("< Назад", callback_data="main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# ==============================
#  ОТЗЫВЫ
# ==============================

async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало сбора отзыва."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Будем рады вашему отзыву!\n\n"
        "Напишите сообщение, и мы обязательно его прочитаем.\n"
        "(Для отмены введите /cancel)"
    )
    return 0


async def feedback_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получили отзыв."""
    feedback_text = update.message.text
    user = update.effective_user

    logger.info("Отзыв от %s (@%s): %s", user.full_name, user.username, feedback_text)

    # Отправляем отзыв администратору
    admin_msg = (
        "💬 Новый отзыв!\n\n"
        f"От: {user.full_name}"
    )
    if user.username:
        admin_msg += f" (@{user.username})"
    admin_msg += f"\n\nТекст: {feedback_text}"
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)

    keyboard = [[InlineKeyboardButton("На главную", callback_data="main")]]
    await update.message.reply_text(
        "Спасибо за ваш отзыв! Мы ценим каждое мнение.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ConversationHandler.END


# ==============================
#  ЗАПУСК
# ==============================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Обработчик записи на услугу (ConversationHandler)
    appointment_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(appointment_start, pattern="^appointment$")],
        states={
            APPT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, appointment_name)],
            APPT_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, appointment_service)],
            APPT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, appointment_date)],
            APPT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, appointment_time)],
        },
        fallbacks=[CommandHandler("cancel", appointment_cancel)],
        per_message=False,
    )

    # Обработчик отзывов (ConversationHandler)
    feedback_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(feedback_start, pattern="^feedback$")],
        states={
            0: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_receive)],
        },
        fallbacks=[CommandHandler("cancel", appointment_cancel)],
        per_message=False,
    )

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(appointment_handler)
    app.add_handler(feedback_handler)
    app.add_handler(CallbackQueryHandler(show_service_categories, pattern="^services$"))
    app.add_handler(CallbackQueryHandler(show_service_items, pattern="^svc_"))
    app.add_handler(CallbackQueryHandler(show_masters, pattern="^masters$"))
    app.add_handler(CallbackQueryHandler(show_promos, pattern="^promos$"))
    app.add_handler(CallbackQueryHandler(show_about, pattern="^about$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^main$"))

    logger.info("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()

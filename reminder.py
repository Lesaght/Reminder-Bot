import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, ConversationHandler, \
    MessageHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

REMINDER_TEXT, TIME_SELECTION = range(2)

TIME_OPTIONS = [
    [
        InlineKeyboardButton("10 мин", callback_data='10'),
        InlineKeyboardButton("30 мин", callback_data='30'),
        InlineKeyboardButton("1 час", callback_data='60')
    ],
    [
        InlineKeyboardButton("3 часа", callback_data='180'),
        InlineKeyboardButton("6 часов", callback_data='360'),
        InlineKeyboardButton("12 часов", callback_data='720')
    ],
    [
        InlineKeyboardButton("1 день", callback_data='1440'),
        InlineKeyboardButton("3 дня", callback_data='4320'),
        InlineKeyboardButton("Ввести вручную ✏️", callback_data='custom')
    ],
    [
        InlineKeyboardButton("◀️ Назад", callback_data='back'),
        InlineKeyboardButton("❌ Отмена", callback_data='cancel')
    ]
]


def format_duration(minutes: int) -> str:
    days = minutes // 1440
    hours = (minutes % 1440) // 60
    mins = minutes % 60
    parts = []
    if days > 0:
        parts.append(f"{days} дн")
    if hours > 0:
        parts.append(f"{hours} час")
    if mins > 0 and days == 0:
        parts.append(f"{mins} мин")
    return " ".join(parts) if parts else "0 мин"


def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Привет! Я бот-напоминалка. Введи сюда свой текст для напоминания👇")
    return REMINDER_TEXT


def get_reminder_text(update: Update, context: CallbackContext) -> int:
    context.user_data['reminder_text'] = update.message.text
    keyboard = InlineKeyboardMarkup(TIME_OPTIONS)
    update.message.reply_text("Выбери время или введи в формате [ЧЧ:ММ]:", reply_markup=keyboard)
    return TIME_SELECTION


def time_selection(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    if query.data == 'custom':
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data='back')]])
        query.edit_message_text(
            "Введи время в формате <b>ЧЧ:ММ</b> (например, 02:30) или как <b>1д 2ч 30м</b>:",
            parse_mode='HTML',
            reply_markup=keyboard
        )
        return TIME_SELECTION

    elif query.data == 'back':
        query.edit_message_text(text="Введи текст напоминания:", reply_markup=None)
        return REMINDER_TEXT

    elif query.data == 'cancel':
        return cancel(update, context)

    else:
        selected_minutes = int(query.data)
        schedule_reminder(update, context, selected_minutes)
        return ConversationHandler.END


def manual_time_input(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text.strip().lower()
    minutes = 0

    try:
        if 'д' in user_input or 'ч' in user_input or 'м' in user_input:
            parts = user_input.split()
            for part in parts:
                if 'д' in part:
                    minutes += int(part.replace('д', '')) * 1440
                elif 'ч' in part:
                    minutes += int(part.replace('ч', '')) * 60
                elif 'м' in part:
                    minutes += int(part.replace('м', ''))
        elif ':' in user_input:
            hours, mins = map(int, user_input.split(':'))
            minutes = hours * 60 + mins
        else:
            raise ValueError
    except:
        update.message.reply_text("❌ Неверный формат. Попробуй еще раз.")
        return TIME_SELECTION

    schedule_reminder(update, context, minutes)
    return ConversationHandler.END


def schedule_reminder(update: Update, context: CallbackContext, minutes: int):
    chat_id = update.effective_chat.id
    text = context.user_data.get('reminder_text', '')
    due = minutes * 60

    context.job_queue.run_once(
        send_reminder,
        due,
        context={'chat_id': chat_id, 'text': text}
    )

    formatted_time = format_duration(minutes)
    update.effective_message.reply_text(f"✅ Напоминание установлено через {formatted_time}!")


def send_reminder(context: CallbackContext) -> None:
    job = context.job
    context.bot.send_message(job.context['chat_id'], text=f'🔔 Напоминание: {job.context["text"]}')


def cancel(update: Update, context: CallbackContext) -> int:
    if update.callback_query:
        update.callback_query.answer()
        update.callback_query.edit_message_text(text='❌ Отменено.')
    else:
        update.message.reply_text('❌ Отменено.')
    return ConversationHandler.END


def main() -> None:
    updater = Updater("ВАШ ТОКЕН")  # Твой токен Телеграм бота от @BotFather
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REMINDER_TEXT: [MessageHandler(Filters.text & ~Filters.command, get_reminder_text)],
            TIME_SELECTION: [
                CallbackQueryHandler(time_selection),
                MessageHandler(Filters.text & ~Filters.command, manual_time_input)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

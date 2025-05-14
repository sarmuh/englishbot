import logging
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from savol import questions
import re

# Логирование
logging.basicConfig(level=logging.INFO)

user_data = {}

# Парсинг одного вопроса
def parse_question(q_text):
    lines = q_text.strip().split('\n')
    question = lines[0]
    options = []
    correct_answer_text = None

    for line in lines[1:]:
        line = line.strip()

        # Определяем, правильный ли ответ
        is_correct = '*' in line

        # Удаляем *, если есть
        line = line.replace('*', '').strip()

        # Удаляем префиксы A), B), C), D) и т.п., если они есть
        line = re.sub(r'^[A-Da-d]\)', '', line).strip()

        if is_correct:
            correct_answer_text = line

        options.append(line)

    return question, options, correct_answer_text

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Nechta test ishlamoqchisiz /test_5, /test_10, /test_25, /test_50, /test_100, /test_200 yoki hammasini /test_all testni boshlash uchun tanlang.")

# Обработчик команд теста
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text
    if command == "/test_5":
        count = 5
    elif command == "/test_10":
        count = 10
    elif command == "/test_25":
        count = 25
    elif command == "/test_50":
        count = 50
    elif command == "/test_100":
        count = 100
    elif command == "/test_200":
        count = 200
    else:
        count = len(questions)

    sample = random.sample(questions, min(count, len(questions)))
    test_data = []

    for q in sample:
        q_text, options, correct_text = parse_question(q)
        random.shuffle(options)
        test_data.append({
            'text': q_text,
            'options': options,
            'correct': correct_text
        })

    user_data[update.effective_user.id] = {
        'questions': test_data,
        'current': 0,
        'correct_answers': 0,
        'answers': []
    }

    await send_question(update, context)
'''
# Отправка текущего вопроса
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = user_data.get(update.effective_user.id)
    if data is None:
        return

    i = data['current']
    if i >= len(data['questions']):
        await show_results(update)
        return

    q = data['questions'][i]
    options = q['options']
    q_text = f"{i+1}) {q['text']}\n" + "\n".join([f"{chr(65 + idx)}) {opt}" for idx, opt in enumerate(options)])
    keyboard = [[chr(65 + i)] for i in range(len(options))]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    # Устанавливаем таймер на 120 секунд, после чего автоматически перейдем к следующему вопросу
    context.job_queue.run_once(timeout_handler, 120, data=update, name=f"timeout_{update.effective_user.id}")


    await update.message.reply_text(q_text, reply_markup=reply_markup)
'''
# Вопрос с таймером на 60 секунд
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = user_data.get(update.effective_user.id)
    if data is None:
        return

    i = data['current']
    if i >= len(data['questions']):
        await show_results(update)
        return

    q = data['questions'][i]
    options = q['options']
    q_text = f"{i+1}) {q['text']}\n" + "\n".join([f"{chr(65 + idx)}) {opt}" for idx, opt in enumerate(options)])
    keyboard = [[chr(65 + i)] for i in range(len(options))]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    # ❗ Удаляем предыдущую задачу, если она осталась
    job_name = f"timeout_{update.effective_user.id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()

    # ⏰ Устанавливаем таймер на 60 секунд
    context.job_queue.run_once(timeout_handler, 60, data=update, name=job_name)

    await update.message.reply_text(q_text, reply_markup=reply_markup)

# Тайм-аут обработчик
'''
async def timeout_handler(context: ContextTypes.DEFAULT_TYPE):
    update = context.job.data  # Получаем update из data
    user_id = update.effective_user.id

    if user_id in user_data:
        data = user_data[user_id]
        if data['current'] < len(data['questions']):
            q = data['questions'][data['current']]
            correct_letter = chr(65 + q['options'].index(q['correct']))
            await update.message.reply_text(f"⏰ Vaqt tugadi! To‘g‘ri javob: {correct_letter}) {q['correct']}")
            data['current'] += 1
            await send_question(update, context)
'''
async def timeout_handler(context: ContextTypes.DEFAULT_TYPE):
    update = context.job.data
    user_id = update.effective_user.id

    if user_id in user_data:
        data = user_data[user_id]
        if data['current'] < len(data['questions']):
            q = data['questions'][data['current']]
            correct_letter = chr(65 + q['options'].index(q['correct']))
            await update.message.reply_text(f"⏰ Vaqt tugadi! To‘g‘ri javob: {correct_letter}) {q['correct']}")
            data['current'] += 1
            await send_question(update, context)


# Обработка ответа пользователя
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data.get(user_id)
    if data is None:
        await update.message.reply_text("Siz testni boshlamadingiz.")
        return

    user_answer_letter = update.message.text.upper()
    i = data['current']
    q = data['questions'][i]

    try:
        idx = ord(user_answer_letter) - 65
        user_answer_text = q['options'][idx]
    except (IndexError, TypeError):
        await update.message.reply_text("Iltimos, A, B, C yoki D variantlarini tanlang.")
        return

    is_correct = user_answer_text == q['correct']
    correct_letter = chr(65 + q['options'].index(q['correct']))

    data['answers'].append((q['text'], user_answer_letter, correct_letter))
    if is_correct:
        data['correct_answers'] += 1
        await update.message.reply_text("✅ To'g'ri javob!")
    else:
        await update.message.reply_text(f"❌ Xato javob! To'g'ri javob: {correct_letter}) {q['correct']}")

    data['current'] += 1
    await send_question(update, context)

# Итоговые результаты
async def show_results(update: Update):
    data = user_data.get(update.effective_user.id)
    result_lines = [
        f"✅ To'g'ri javoblar: {data['correct_answers']} jami {len(data['questions'])} dan",
        ""
    ]
    for i, (q, user_ans, correct_ans) in enumerate(data['answers']):
        status = "✅" if user_ans == correct_ans else "❌"
        result_lines.append(f"{i+1}. {status} Siz tanladingiz: {user_ans}, To'g'risi: {correct_ans}")
    await update.message.reply_text("\n".join(result_lines))

# Команда /stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot to'xtadi.")
    await context.application.shutdown()

# Запуск бота
def main():
    app = ApplicationBuilder().token("7624195497:AAGv--qJThE2gV9jlnVj2HE4wqTDygZERd0").build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test_5", start_test))
    app.add_handler(CommandHandler("test_10", start_test))
    app.add_handler(CommandHandler("test_25", start_test))
    app.add_handler(CommandHandler("test_50", start_test))
    app.add_handler(CommandHandler("test_100", start_test))
    app.add_handler(CommandHandler("test_200", start_test))
    app.add_handler(CommandHandler("test_all", start_test))
    app.add_handler(CommandHandler("stop", stop))

    # Обработчик для текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    app.run_polling()

# Обязательная инициализация JobQueue
async def post_init(app):
    app.job_queue.set_application(app)


if __name__ == "__main__":
    main()

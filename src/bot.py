import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
from src.fetcher import PowerDataFetcher
from src.parser import PowerScheduleParser
from src.scheduler import WorkScheduler
from src.history import ScheduleHistory

load_dotenv()

user_configs = {}


def get_developer_info() -> str:
    """Інформація про розробника"""
    return "Розробник: @antibiotikphoto"


def format_schedule(outages: list) -> str:
    if not outages:
        return "✅ Світло є весь день"
    times = [f"{o['start']}-{o['end']}" for o in outages]
    return f"❌ Відключення: {', '.join(times)}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚙️ Налаштувати черги", callback_data="setup")],
        [InlineKeyboardButton("ℹ️ Про бота", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Привіт! Я допоможу оптимізувати твій робочий графік.\n\n"
        "🔌 Відстежую графіки відключень у Львові\n"
        "📊 Складаю персональний план\n"
        "🔄 Повідомляю про зміни\n\n"
        "Спочатку налаштуй свої черги відключень:",
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "about":
        await query.message.reply_text(
            "ℹ️ Power Schedule Bot\n\n"
            "Допомагає оптимізувати робочий графік на основі\n"
            "графіків відключень електроенергії у Львові.\n\n"
            "📊 Функції:\n"
            "• Графіки відключень\n"
            "• Персональний план\n"
            "• Відстеження змін\n"
            "• Рекомендації\n\n"
            f"👨‍💻 {get_developer_info()}\n\n"
            "Джерело даних: Львівобленерго"
        )
    elif query.data == "setup":
        await query.message.reply_text(
            "⚙️ Налаштування черг\n\n"
            "Використай команду:\n"
            "/config <група1> <група2>\n\n"
            "Приклад: /config 4.2 6.2"
        )


async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if len(context.args) == 2:
        user_configs[user_id] = {
            "home_group": context.args[0],
            "old_home_group": context.args[1]
        }
        await update.message.reply_text(
            f"✅ Налаштовано!\n"
            f"🏠 Основна квартира: група {context.args[0]}\n"
            f"🏘 Друга квартира: група {context.args[1]}\n\n"
            f"Тепер доступні:\n"
            f"/today - графік на сьогодні\n"
            f"/plan - план на день\n"
            f"/recommend - рекомендація зараз\n"
            f"/changes - перевірити зміни"
        )
    else:
        await update.message.reply_text(
            "⚙️ Налаштування черг\n\n"
            "Використання: /config <група1> <група2>\n"
            "Приклад: /config 4.2 6.2\n\n"
            "Як дізнатись свою чергу:\n"
            "1. Відкрий poweron.loe.lviv.ua/shedule-off\n"
            "2. Введи адресу\n"
            "3. Запам'ятай номер групи"
        )


def _fetch_all_schedules(parser):
    """Отримує всі графіки (Today/Tomorrow) — спільна логіка з CLI"""
    import requests
    resp = requests.get(PowerDataFetcher.API_URL, timeout=10)
    data = resp.json()
    items = data['hydra:member'][0]['menuItems']

    result = []
    for item in items:
        item_name = item.get('name', '')
        html = item.get('rawHtml', '')
        if html:
            date = parser.extract_date(html)
            schedule = parser.parse_all_groups(html)
            result.append({
                'name': item_name,
                'date': date,
                'schedule': schedule,
                'html': html
            })
    return result


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_configs:
        await update.message.reply_text("❌ Спочатку налаштуй черги: /config")
        return

    await update.message.reply_text("⏳ Завантажую графік...")

    parser = PowerScheduleParser()

    try:
        schedules = _fetch_all_schedules(parser)
    except Exception:
        await update.message.reply_text("❌ Не вдалося отримати дані")
        return

    config = user_configs[user_id]

    today_found = any(s['name'] == 'Today' for s in schedules)
    tomorrow_data = next((s for s in schedules if s['name'] == 'Tomorrow'), None)

    if not today_found:
        message = "⚠️ Дані на сьогодні вже недоступні\n\n"

        if tomorrow_data:
            schedule = tomorrow_data['schedule']
            home_outages = schedule.get(config["home_group"], [])
            old_home_outages = schedule.get(config["old_home_group"], [])

            message += f"📅 Графік на завтра ({tomorrow_data['date']})\n\n"
            message += f"🏠 Основна квартира (група {config['home_group']}):\n"
            message += f"{format_schedule(home_outages)}\n\n"
            message += f"🏘 Друга квартира (група {config['old_home_group']}):\n"
            message += f"{format_schedule(old_home_outages)}"

        await update.message.reply_text(message)
        return

    message = ""
    for sched in schedules:
        if sched['name'] in ['Today', 'Tomorrow']:
            schedule = sched['schedule']
            home_outages = schedule.get(config["home_group"], [])
            old_home_outages = schedule.get(config["old_home_group"], [])

            message += f"📅 Графік на {sched['date']} ({sched['name']})\n\n"
            message += f"🏠 Основна квартира (група {config['home_group']}):\n"
            message += f"{format_schedule(home_outages)}\n\n"
            message += f"🏘 Друга квартира (група {config['old_home_group']}):\n"
            message += f"{format_schedule(old_home_outages)}\n\n"

    await update.message.reply_text(message.strip())


async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_configs:
        await update.message.reply_text("❌ Спочатку налаштуй черги: /config")
        return

    await update.message.reply_text("⏳ Складаю план...")

    fetcher = PowerDataFetcher()
    parser = PowerScheduleParser()
    scheduler = WorkScheduler()

    data = fetcher.get_latest_schedule()
    if not data:
        await update.message.reply_text("❌ Не вдалося отримати дані")
        return

    html = data.get("rawHtml", "")
    date = parser.extract_date(html)
    schedule = parser.parse_all_groups(html)

    config = user_configs[user_id]
    home_outages = schedule.get(config["home_group"], [])
    old_home_outages = schedule.get(config["old_home_group"], [])

    current_time = datetime.now()
    current_minutes = current_time.hour * 60 + current_time.minute

    # Збираємо всі ключові моменти часу (як у CLI)
    time_points = {current_minutes, 24 * 60}

    for outage in home_outages + old_home_outages:
        start_h, start_m = map(int, outage["start"].split(":"))
        end_h, end_m = map(int, outage["end"].replace("24:00", "23:59").split(":"))
        time_points.add(start_h * 60 + start_m)
        time_points.add(end_h * 60 + end_m)

    time_points = sorted([t for t in time_points if t >= current_minutes])

    # Формуємо періоди з точними межами
    periods = []
    for i in range(len(time_points) - 1):
        start_min = time_points[i]
        end_min = time_points[i + 1]

        mid_min = (start_min + end_min) // 2
        mid_time = f"{mid_min // 60:02d}:{mid_min % 60:02d}"

        home_power = scheduler.is_power_available(home_outages, mid_time)
        old_home_power = scheduler.is_power_available(old_home_outages, mid_time)

        periods.append({
            'start': start_min,
            'end': end_min,
            'situation': (home_power, old_home_power)
        })

    message = f"📅 План на {date}\n\n"

    for period in periods:
        start_h, start_m = period['start'] // 60, period['start'] % 60
        end_h, end_m = period['end'] // 60, period['end'] % 60
        start = f"{start_h:02d}:{start_m:02d}"
        end = f"{end_h:02d}:{end_m:02d}"
        home, old_home = period['situation']

        if home and old_home:
            message += f"⏰ {start}-{end}: ✅ Світло в обох групах\n"
        elif home and not old_home:
            message += f"⏰ {start}-{end}: 🏠 Група {config['home_group']}\n"
        elif not home and old_home:
            message += f"⏰ {start}-{end}: 🏘 Група {config['old_home_group']}\n"
        else:
            message += f"⏰ {start}-{end}: ❌ Світла немає в обох групах\n"

    start_time = f"{current_time.hour:02d}:{current_time.minute:02d}"
    home_hours = scheduler.calculate_available_hours(home_outages, start_time, "23:59")
    old_home_hours = scheduler.calculate_available_hours(old_home_outages, start_time, "23:59")

    message += f"\n💡 Підсумок:\n"
    message += f"🏠 Група {config['home_group']}: {home_hours:.1f}h\n"
    message += f"🏘 Група {config['old_home_group']}: {old_home_hours:.1f}h\n"
    message += f"\n✅ Рекомендація: Група {config['home_group'] if home_hours >= old_home_hours else config['old_home_group']}"

    await update.message.reply_text(message)


async def changes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_configs:
        await update.message.reply_text("❌ Спочатку налаштуй черги: /config")
        return

    await update.message.reply_text("⏳ Перевіряю зміни...")

    parser = PowerScheduleParser()
    history = ScheduleHistory(f".bot_history_{user_id}.json")

    try:
        schedules = _fetch_all_schedules(parser)
    except Exception:
        await update.message.reply_text("❌ Не вдалося отримати дані")
        return

    config = user_configs[user_id]
    has_changes = False
    message = ""

    for sched in schedules:
        if sched['name'] in ['Today', 'Tomorrow']:
            date = sched['date']
            schedule = sched['schedule']

            our_schedule = {
                config["home_group"]: schedule.get(config["home_group"], []),
                config["old_home_group"]: schedule.get(config["old_home_group"], [])
            }

            changes_list = history.get_changes(date, our_schedule)

            if changes_list:
                has_changes = True
                message += f"🔄 Зміни в графіку на {date} ({sched['name']}):\n\n"
                for change in changes_list:
                    message += f"• {change}\n"
                message += "\n"

            history.save(date, our_schedule)

    if not has_changes:
        message = "✅ Змін немає"

    await update.message.reply_text(message.strip())


async def recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_configs:
        await update.message.reply_text("❌ Спочатку налаштуй черги: /config")
        return

    await update.message.reply_text("⏳ Аналізую...")

    fetcher = PowerDataFetcher()
    parser = PowerScheduleParser()
    scheduler = WorkScheduler()

    data = fetcher.get_latest_schedule()
    if not data:
        await update.message.reply_text("❌ Не вдалося отримати дані")
        return

    html = data.get("rawHtml", "")
    schedule = parser.parse_all_groups(html)

    config = user_configs[user_id]
    current_time = datetime.now().strftime("%H:%M")

    result = scheduler.recommend(config["home_group"], config["old_home_group"], schedule, current_time)

    location_emoji = "🏠" if result["location"] == config["home_group"] else "🏘"
    location_name = "Основна квартира" if result["location"] == config["home_group"] else "Друга квартира"

    message = f"💡 Рекомендація (зараз {current_time}):\n\n"
    message += f"{location_emoji} {location_name} (група {result['location']})\n"
    message += f"💬 {result['reason']}"

    await update.message.reply_text(message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Доступні команди:\n\n"
        "/config <група1> <група2> - налаштувати черги\n"
        "/today - графік на сьогодні\n"
        "/plan - план на день\n"
        "/changes - перевірити зміни\n"
        "/recommend - рекомендація зараз\n"
        "/help - ця довідка\n\n"
        f"👨‍💻 {get_developer_info()}"
    )


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("❌ Помилка: TELEGRAM_BOT_TOKEN не знайдено в .env")
        return
    
    app = Application.builder().token(token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("config", config))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CommandHandler("changes", changes))
    app.add_handler(CommandHandler("recommend", recommend))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤖 Бот запущено...")
    app.run_polling()


if __name__ == "__main__":
    main()

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


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_configs:
        await update.message.reply_text("❌ Спочатку налаштуй черги: /config")
        return
    
    await update.message.reply_text("⏳ Завантажую графік...")
    
    fetcher = PowerDataFetcher()
    parser = PowerScheduleParser()
    
    import requests
    resp = requests.get('https://api.loe.lviv.ua/api/menus?page=1&type=photo-grafic')
    data = resp.json()
    items = data['hydra:member'][0]['menuItems']
    
    today_data = next((item for item in items if item.get('name') == 'Today' and item.get('rawHtml')), None)
    tomorrow_data = next((item for item in items if item.get('name') == 'Tomorrow' and item.get('rawHtml')), None)
    
    config = user_configs[user_id]
    
    if not today_data:
        message = "⚠️ Дані на сьогодні вже недоступні\n\n"
        
        if tomorrow_data:
            html = tomorrow_data.get("rawHtml", "")
            date = parser.extract_date(html)
            schedule = parser.parse_all_groups(html)
            
            home_outages = schedule.get(config["home_group"], [])
            old_home_outages = schedule.get(config["old_home_group"], [])
            
            message += f"📅 Графік на завтра ({date})\n\n"
            message += f"🏠 Основна квартира (група {config['home_group']}):\n"
            message += f"{format_schedule(home_outages)}\n\n"
            message += f"🏘 Друга квартира (група {config['old_home_group']}):\n"
            message += f"{format_schedule(old_home_outages)}"
        
        await update.message.reply_text(message)
        return
    
    html = today_data.get("rawHtml", "")
    date = parser.extract_date(html)
    schedule = parser.parse_all_groups(html)
    
    home_outages = schedule.get(config["home_group"], [])
    old_home_outages = schedule.get(config["old_home_group"], [])
    
    message = f"📅 Графік на {date}\n\n"
    message += f"🏠 Основна квартира (група {config['home_group']}):\n"
    message += f"{format_schedule(home_outages)}\n\n"
    message += f"🏘 Друга квартира (група {config['old_home_group']}):\n"
    message += f"{format_schedule(old_home_outages)}"
    
    await update.message.reply_text(message)


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
    
    current_hour = datetime.now().hour
    
    # Аналіз по годинах
    periods = []
    current_period = None
    
    for hour in range(current_hour, 24):
        time_str = f"{hour:02d}:00"
        home_power = scheduler.is_power_available(home_outages, time_str)
        old_home_power = scheduler.is_power_available(old_home_outages, time_str)
        situation = (home_power, old_home_power)
        
        if current_period is None or current_period['situation'] != situation:
            if current_period:
                periods.append(current_period)
            current_period = {'start': hour, 'end': hour + 1, 'situation': situation}
        else:
            current_period['end'] = hour + 1
    
    if current_period:
        periods.append(current_period)
    
    message = f"📅 План на {date}\n\n"
    
    for period in periods:
        start = f"{period['start']:02d}:00"
        end = f"{period['end']:02d}:00" if period['end'] < 24 else "24:00"
        home, old_home = period['situation']
        
        if home and old_home:
            message += f"⏰ {start}-{end}: ✅ Світло скрізь\n"
        elif home and not old_home:
            message += f"⏰ {start}-{end}: 🏠 Тільки вдома\n"
        elif not home and old_home:
            message += f"⏰ {start}-{end}: 🏘 Тільки на другій\n"
        else:
            message += f"⏰ {start}-{end}: ❌ Світла немає\n"
    
    end_time = "23:59"
    home_hours = scheduler.calculate_available_hours(home_outages, f"{current_hour:02d}:00", end_time)
    old_home_hours = scheduler.calculate_available_hours(old_home_outages, f"{current_hour:02d}:00", end_time)
    
    message += f"\n💡 Підсумок:\n🏠 Вдома: {home_hours:.1f}h\n🏘 Друга: {old_home_hours:.1f}h\n"
    message += f"\n✅ Краще {'вдома' if home_hours >= old_home_hours else 'на другій'}"
    
    await update.message.reply_text(message)


async def changes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_configs:
        await update.message.reply_text("❌ Спочатку налаштуй черги: /config")
        return
    
    await update.message.reply_text("⏳ Перевіряю зміни...")
    
    fetcher = PowerDataFetcher()
    parser = PowerScheduleParser()
    history = ScheduleHistory(f".bot_history_{user_id}.json")
    
    data = fetcher.get_latest_schedule()
    if not data:
        await update.message.reply_text("❌ Не вдалося отримати дані")
        return
    
    html = data.get("rawHtml", "")
    date = parser.extract_date(html)
    schedule = parser.parse_all_groups(html)
    
    config = user_configs[user_id]
    our_schedule = {
        config["home_group"]: schedule.get(config["home_group"], []),
        config["old_home_group"]: schedule.get(config["old_home_group"], [])
    }
    
    changes_list = history.get_changes(date, our_schedule)
    
    if changes_list:
        message = f"🔄 Зміни в графіку на {date}:\n\n"
        for change in changes_list:
            message += f"• {change}\n"
    else:
        message = "✅ Змін немає"
    
    history.save(date, our_schedule)
    await update.message.reply_text(message)


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
    
    location_emoji = "🏠" if result["location"] == "home" else "🏘"
    location_name = "Основна квартира" if result["location"] == "home" else "Друга квартира"
    
    message = f"💡 Рекомендація (зараз {current_time}):\n\n{location_emoji} {location_name}\n💬 {result['reason']}"
    
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

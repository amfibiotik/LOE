# Налаштування Telegram Бота

## Крок 1: Створення бота

1. Відкрийте Telegram і знайдіть [@BotFather](https://t.me/botfather)
2. Надішліть команду `/newbot`
3. Введіть ім'я бота (наприклад: "Lviv Power Schedule")
4. Введіть username бота (має закінчуватись на `bot`, наприклад: `lviv_power_bot`)
5. BotFather надасть вам **токен** - збережіть його!

Приклад токену: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

## Крок 2: Отримання посилання на Threads

1. Відкрийте додаток **Threads** (від Instagram/Meta)
2. Перейдіть на свій профіль
3. Натисніть на **три крапки** (⋯) або **Share Profile**
4. Виберіть **Copy Link** або **Share Profile Link**
5. Ваше посилання буде виглядати як: `https://www.threads.net/@your_username`

**Альтернативно:**
- Просто додайте `@` перед вашим username: `@your_username`
- Або повне посилання: `https://www.threads.net/@your_username`

## Крок 3: Додавання вашого посилання в бота

Відредагуйте файл `src/bot.py`, знайдіть функцію `get_developer_info()`:

```python
def get_developer_info() -> str:
    """Інформація про розробника"""
    return "Розробник: @your_threads_username"  # <-- Замініть тут
```

Замініть `@your_threads_username` на ваш username або повне посилання.

**Приклади:**
```python
# Варіант 1: Username
return "Розробник: @john_doe"

# Варіант 2: Повне посилання
return "Розробник: https://www.threads.net/@john_doe"

# Варіант 3: З текстом
return "👨‍💻 Розробник: @john_doe | Львів"
```

## Крок 4: Налаштування проекту

Створіть файл `.env` у корені проекту:

```bash
TELEGRAM_BOT_TOKEN=ваш_токен_тут
```

**ВАЖЛИВО:** Додайте `.env` до `.gitignore`, щоб не закомітити токен!

## Крок 3: Запуск бота

```bash
python -m src.bot
```

## Крок 4: Використання

Знайдіть свого бота в Telegram за username і натисніть `/start`

### Доступні команди:

- `/start` - Початок роботи
- `/today` - Графік відключень на сьогодні
- `/tomorrow` - Графік на завтра
- `/recommend` - Рекомендація де працювати зараз
- `/config` - Налаштувати черги відключень

### Налаштування черг

1. Надішліть `/config`
2. Введіть чергу для основної квартири (наприклад: `1.1`)
3. Введіть чергу для другої квартири (наприклад: `3.2`)

Бот запам'ятає ваші налаштування.

## Автоматичні сповіщення (опціонально)

Щоб отримувати ранкові рекомендації:

1. Надішліть `/notify on`
2. Бот щодня о 8:00 надсилатиме рекомендацію

Вимкнути: `/notify off`

## Деплой (для постійної роботи)

### Варіант 1: На власному сервері

```bash
# Встановіть screen або tmux
screen -S powerbot

# Запустіть бота
python -m src.bot

# Відключіться: Ctrl+A, потім D
```

### Варіант 2: Heroku (безкоштовно)

1. Створіть акаунт на [Heroku](https://heroku.com)
2. Встановіть [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
3. Виконайте:

```bash
heroku login
heroku create your-app-name
heroku config:set TELEGRAM_BOT_TOKEN=ваш_токен
git push heroku main
```

### Варіант 3: Railway (безкоштовно)

1. Зареєструйтесь на [Railway](https://railway.app)
2. Підключіть GitHub репозиторій
3. Додайте змінну середовища `TELEGRAM_BOT_TOKEN`
4. Railway автоматично задеплоїть бота

## Troubleshooting

**Бот не відповідає:**
- Перевірте, чи правильний токен у `.env`
- Перевірте, чи запущений скрипт `python -m src.bot`
- Подивіться логи на помилки

**Помилка "Unauthorized":**
- Токен неправильний або застарів
- Створіть нового бота через BotFather

**Бот відповідає повільно:**
- Перевірте інтернет-з'єднання
- API Львівобленерго може бути повільним

# Швидкий старт

## 1. Встановлення

```bash
# Клонуйте або створіть проект
cd power-schedule

# Створіть віртуальне середовище
python3 -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

# Встановіть залежності
pip install -r requirements.txt
```

## 2. Налаштування

Відредагуйте `config.yaml` - вкажіть ваші черги відключень:

```yaml
locations:
  home:
    name: "Основна квартира"
    group: "1.1"  # <-- ваша черга
  old_home:
    name: "Стара квартира"
    group: "3.2"  # <-- ваша черга
```

## 3. Використання CLI

```bash
# Активуйте віртуальне середовище
source venv/bin/activate

# Подивіться графік на сьогодні
python -m src.cli today

# Отримайте рекомендацію де працювати
python -m src.cli recommend
```

## 4. Telegram Бот (опціонально)

Детальна інструкція: [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)

Коротко:
1. Створіть бота через [@BotFather](https://t.me/botfather)
2. Скопіюйте `.env.example` в `.env` і вставте токен
3. Запустіть: `python -m src.bot`

## Тестування

```bash
pytest tests/ -v
```

## Як дізнатись свою чергу?

1. Відкрийте https://poweron.loe.lviv.ua/shedule-off
2. Введіть вашу адресу
3. Запам'ятайте номер групи (наприклад: 1.1, 3.2, тощо)

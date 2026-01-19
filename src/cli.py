import sys
import yaml
from datetime import datetime
from src.fetcher import PowerDataFetcher
from src.parser import PowerScheduleParser
from src.scheduler import WorkScheduler
from src.history import ScheduleHistory


def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def format_schedule(outages: list) -> str:
    if not outages:
        return "✅ Світло є весь день"
    
    times = [f"{o['start']}-{o['end']}" for o in outages]
    return f"❌ Відключення: {', '.join(times)}"


def get_schedule_data(fetcher, parser, name_filter=None):
    """Отримує дані графіку (today або tomorrow)"""
    import requests
    resp = requests.get('https://api.loe.lviv.ua/api/menus?page=1&type=photo-grafic')
    data = resp.json()
    items = data['hydra:member'][0]['menuItems']
    
    result = []
    for item in items:
        item_name = item.get('name', '')
        html = item.get('rawHtml', '')
        
        if html and (name_filter is None or item_name == name_filter):
            date = parser.extract_date(html)
            schedule = parser.parse_all_groups(html)
            result.append({
                'name': item_name,
                'date': date,
                'schedule': schedule,
                'html': html
            })
    
    return result


def cmd_today():
    config = load_config()
    fetcher = PowerDataFetcher()
    parser = PowerScheduleParser()
    
    print("Завантаження графіку...")
    schedules = get_schedule_data(fetcher, parser)
    
    today_found = any(s['name'] == 'Today' for s in schedules)
    tomorrow_data = next((s for s in schedules if s['name'] == 'Tomorrow'), None)
    
    if not today_found:
        print("\n⚠️  Дані на сьогодні вже недоступні\n")
        
        if tomorrow_data:
            print(f"📅 Графік на завтра ({tomorrow_data['date']})\n")
            for loc_key, loc_data in config["locations"].items():
                group = loc_data["group"]
                outages = tomorrow_data['schedule'].get(group, [])
                print(f"{loc_data['name']} (група {group}):")
                print(f"  {format_schedule(outages)}\n")
        return
    
    for sched in schedules:
        if sched['name'] in ['Today', 'Tomorrow']:
            date = sched['date']
            schedule = sched['schedule']
            
            print(f"\n📅 Графік на {date} ({sched['name']})\n")
            
            for loc_key, loc_data in config["locations"].items():
                group = loc_data["group"]
                outages = schedule.get(group, [])
                print(f"{loc_data['name']} (група {group}):")
                print(f"  {format_schedule(outages)}\n")


def cmd_plan():
    """Складає план на день"""
    config = load_config()
    fetcher = PowerDataFetcher()
    parser = PowerScheduleParser()
    scheduler = WorkScheduler()
    
    print("Завантаження графіку...")
    schedules = get_schedule_data(fetcher, parser, "Today")
    
    if not schedules:
        print("❌ Не вдалося отримати дані")
        return
    
    sched = schedules[0]
    date = sched['date']
    schedule = sched['schedule']
    
    home_group = config["locations"]["home"]["group"]
    old_home_group = config["locations"]["old_home"]["group"]
    
    home_outages = schedule.get(home_group, [])
    old_home_outages = schedule.get(old_home_group, [])
    
    print(f"\n📅 План на {date}\n")
    
    # Графічне відображення
    def create_timeline(outages, label):
        blocks = []
        for quarter in range(96):
            minutes = quarter * 15
            time_str = f"{minutes // 60:02d}:{minutes % 60:02d}"
            has_power = scheduler.is_power_available(outages, time_str)
            blocks.append('░' if has_power else '▓')
        
        print(f"{label}: {''.join(blocks)}")
    
    create_timeline(home_outages, f"Група {home_group}")
    create_timeline(old_home_outages, f"Група {old_home_group}")
    
    # Шкала часу
    labels = []
    for hour in range(0, 25, 3):
        h = hour if hour < 24 else 0
        labels.append(f"{h:02d}:00")
    
    # Кожна година = 4 символи (15хв кожен), двокрапка має бути на позиції години
    timeline = ""
    for i, label in enumerate(labels):
        if i == 0:
            timeline += label
        else:
            # 3 години = 12 символів, мінус довжина попереднього лейбла
            spacing = 12 - len(labels[i-1]) + len(label) // 2
            timeline += " " * spacing + label
    
    print(f"            {timeline}\n")
    
    # Збираємо всі ключові моменти часу
    current_time = datetime.now()
    current_minutes = current_time.hour * 60 + current_time.minute
    
    time_points = {current_minutes, 24 * 60}  # Поточний час і кінець дня
    
    for outage in home_outages + old_home_outages:
        start_h, start_m = map(int, outage["start"].split(":"))
        end_h, end_m = map(int, outage["end"].replace("24:00", "23:59").split(":"))
        time_points.add(start_h * 60 + start_m)
        time_points.add(end_h * 60 + end_m)
    
    time_points = sorted([t for t in time_points if t >= current_minutes])
    
    # Формуємо періоди
    periods = []
    for i in range(len(time_points) - 1):
        start_min = time_points[i]
        end_min = time_points[i + 1]
        
        # Перевіряємо середину періоду
        mid_min = (start_min + end_min) // 2
        mid_time = f"{mid_min // 60:02d}:{mid_min % 60:02d}"
        
        home_power = scheduler.is_power_available(home_outages, mid_time)
        old_home_power = scheduler.is_power_available(old_home_outages, mid_time)
        
        periods.append({
            'start': start_min,
            'end': end_min,
            'situation': (home_power, old_home_power)
        })
    
    # Виводимо періоди
    for period in periods:
        start_h, start_m = period['start'] // 60, period['start'] % 60
        end_h, end_m = period['end'] // 60, period['end'] % 60
        start = f"{start_h:02d}:{start_m:02d}"
        end = f"{end_h:02d}:{end_m:02d}"
        home, old_home = period['situation']
        
        if home and old_home:
            print(f"⏰ {start}-{end}: ✅ Світло в обох групах")
        elif home and not old_home:
            print(f"⏰ {start}-{end}: Група {home_group}")
        elif not home and old_home:
            print(f"⏰ {start}-{end}: Група {old_home_group}")
        else:
            print(f"⏰ {start}-{end}: ❌ Світла немає в обох групах")
    
    # Загальна рекомендація
    start_time = f"{current_time.hour:02d}:{current_time.minute:02d}"
    home_hours = scheduler.calculate_available_hours(home_outages, start_time, "23:59")
    old_home_hours = scheduler.calculate_available_hours(old_home_outages, start_time, "23:59")
    
    print(f"\n💡 Підсумок:")
    print(f"Група {home_group}: {home_hours:.1f}h світла")
    print(f"Група {old_home_group}: {old_home_hours:.1f}h світла")
    
    if home_hours >= old_home_hours:
        print(f"\n✅ Рекомендація: Група {home_group}")
    else:
        print(f"\n✅ Рекомендація: Група {old_home_group}")


def cmd_changes():
    """Показує зміни в графіку"""
    config = load_config()
    fetcher = PowerDataFetcher()
    parser = PowerScheduleParser()
    history = ScheduleHistory()
    
    print("Перевірка змін...")
    schedules = get_schedule_data(fetcher, parser)
    
    has_changes = False
    
    for sched in schedules:
        if sched['name'] in ['Today', 'Tomorrow']:
            date = sched['date']
            schedule = sched['schedule']
            
            # Фільтруємо тільки наші групи
            our_schedule = {
                config["locations"]["home"]["group"]: schedule.get(config["locations"]["home"]["group"], []),
                config["locations"]["old_home"]["group"]: schedule.get(config["locations"]["old_home"]["group"], [])
            }
            
            changes = history.get_changes(date, our_schedule)
            
            if changes:
                has_changes = True
                print(f"\n🔄 Зміни в графіку на {date} ({sched['name']}):\n")
                for change in changes:
                    print(f"  • {change}")
            
            # Зберігаємо новий графік
            history.save(date, our_schedule)
    
    if not has_changes:
        print("\n✅ Змін немає")


def cmd_recommend():
    config = load_config()
    fetcher = PowerDataFetcher()
    parser = PowerScheduleParser()
    scheduler = WorkScheduler()
    
    print("Завантаження графіку...")
    data = fetcher.get_latest_schedule()
    
    if not data:
        print("❌ Не вдалося отримати дані")
        return
    
    html = data.get("rawHtml", "")
    schedule = parser.parse_all_groups(html)
    
    home_group = config["locations"]["home"]["group"]
    old_home_group = config["locations"]["old_home"]["group"]
    current_time = datetime.now().strftime("%H:%M")
    
    result = scheduler.recommend(
        home_group,
        old_home_group,
        schedule,
        current_time
    )
    
    print(f"\n💡 Рекомендація (зараз {current_time}):\n")
    
    print(f"📍 Група {result['location']}")
    print(f"💬 {result['reason']}\n")


def main():
    if len(sys.argv) < 2:
        print("Використання:")
        print("  python -m src.cli today     - графіки на сьогодні і завтра")
        print("  python -m src.cli plan      - план на сьогодні")
        print("  python -m src.cli changes   - зміни в графіках")
        print("  python -m src.cli recommend - рекомендація зараз")
        return
    
    command = sys.argv[1]
    
    if command == "today":
        cmd_today()
    elif command == "plan":
        cmd_plan()
    elif command == "changes":
        cmd_changes()
    elif command == "recommend":
        cmd_recommend()
    else:
        print(f"Невідома команда: {command}")


if __name__ == "__main__":
    main()

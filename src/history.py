import json
import os
from datetime import datetime
from typing import List


class ScheduleHistory:
    def __init__(self, filename: str = ".schedule_history.json"):
        self.filename = filename
        self.data = self._load()

    def _load(self) -> dict:
        """Завантажує історію з файлу"""
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_to_file(self):
        """Зберігає історію у файл"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def save(self, date: str, schedule: dict):
        """Зберігає графік на дату (тільки перший раз)"""
        if date not in self.data:
            self.data[date] = schedule
            self._cleanup(date)
            self._save_to_file()

    def _cleanup(self, current_date: str):
        """Видаляє дати, що вже минули"""
        try:
            current = datetime.strptime(current_date, "%d.%m.%Y").date()
        except ValueError:
            return

        expired = [d for d in self.data if d != current_date]
        for d in expired:
            try:
                if datetime.strptime(d, "%d.%m.%Y").date() < current:
                    del self.data[d]
            except ValueError:
                pass

    def get_latest(self, date: str) -> dict:
        """Отримує збережений графік на дату"""
        return self.data.get(date)

    def get_changes(self, date: str, new_schedule: dict) -> List[str]:
        """Порівнює новий графік зі збереженим"""
        old_schedule = self.get_latest(date)

        if not old_schedule:
            return []

        changes = []

        for group in new_schedule.keys():
            old_outages = old_schedule.get(group, [])
            new_outages = new_schedule.get(group, [])

            if old_outages != new_outages:
                changes.append(self._describe_change(group, old_outages, new_outages))

        return changes

    def _describe_change(self, group: str, old: list, new: list) -> str:
        """Описує зміну в графіку"""
        if len(old) == 0 and len(new) > 0:
            return f"Група {group}: додано відключення"
        elif len(old) > 0 and len(new) == 0:
            return f"Група {group}: відключення скасовано ✅"
        elif len(old) < len(new):
            return f"Група {group}: більше відключень"
        elif len(old) > len(new):
            return f"Група {group}: менше відключень ✅"
        else:
            return f"Група {group}: змінено час відключень"

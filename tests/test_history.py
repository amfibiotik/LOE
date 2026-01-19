import pytest
import json
import os
from datetime import datetime
from src.history import ScheduleHistory


def test_save_schedule():
    """Тест збереження графіку"""
    history = ScheduleHistory("test_history.json")
    
    schedule = {
        "4.2": [{"start": "08:00", "end": "11:00"}],
        "6.2": []
    }
    
    history.save("18.01.2026", schedule)
    
    # Перевірка що файл створено
    assert os.path.exists("test_history.json")
    
    # Очистка
    os.remove("test_history.json")


def test_get_changes():
    """Тест виявлення змін"""
    history = ScheduleHistory("test_history.json")
    
    old_schedule = {
        "4.2": [{"start": "08:00", "end": "11:00"}],
        "6.2": []
    }
    
    new_schedule = {
        "4.2": [{"start": "08:00", "end": "12:00"}],  # подовжили
        "6.2": [{"start": "14:00", "end": "17:00"}]   # додали
    }
    
    history.save("18.01.2026", old_schedule)
    changes = history.get_changes("18.01.2026", new_schedule)
    
    assert len(changes) > 0
    assert any("4.2" in c for c in changes)
    assert any("6.2" in c for c in changes)
    
    # Очистка
    os.remove("test_history.json")


def test_no_changes():
    """Тест коли змін немає"""
    history = ScheduleHistory("test_history.json")
    
    schedule = {
        "4.2": [{"start": "08:00", "end": "11:00"}],
        "6.2": []
    }
    
    history.save("18.01.2026", schedule)
    changes = history.get_changes("18.01.2026", schedule)
    
    assert len(changes) == 0
    
    # Очистка
    os.remove("test_history.json")

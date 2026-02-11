import pytest
from src.scheduler import WorkScheduler


def test_recommend_location_both_have_power():
    """Коли в обох локаціях є світло - залишатись вдома"""
    schedule = {
        "1.1": [],  # немає відключень
        "3.2": []   # немає відключень
    }
    
    scheduler = WorkScheduler()
    result = scheduler.recommend("1.1", "3.2", schedule, "10:00")
    
    assert result["location"] == "1.1"
    assert "обох" in result["reason"].lower()


def test_recommend_location_home_no_power():
    """Коли вдома немає світла - їхати на другу квартиру"""
    schedule = {
        "1.1": [{"start": "08:00", "end": "11:30"}],
        "3.2": []
    }
    
    scheduler = WorkScheduler()
    result = scheduler.recommend("1.1", "3.2", schedule, "10:00")
    
    assert result["location"] == "3.2"
    assert "без світла" in result["reason"].lower() or "зі світлом" in result["reason"].lower()


def test_recommend_location_both_no_power():
    """Коли в обох немає світла"""
    schedule = {
        "1.1": [{"start": "08:00", "end": "11:30"}],
        "3.2": [{"start": "08:00", "end": "11:00"}]
    }
    
    scheduler = WorkScheduler()
    result = scheduler.recommend("1.1", "3.2", schedule, "10:00")
    
    assert result["location"] in ["1.1", "3.2"]


def test_is_power_available():
    """Тест перевірки наявності світла в конкретний час"""
    outages = [
        {"start": "08:00", "end": "11:30"},
        {"start": "14:00", "end": "17:00"}
    ]
    
    scheduler = WorkScheduler()
    
    assert scheduler.is_power_available(outages, "07:00") == True
    assert scheduler.is_power_available(outages, "10:00") == False
    assert scheduler.is_power_available(outages, "12:00") == True
    assert scheduler.is_power_available(outages, "15:00") == False
    assert scheduler.is_power_available(outages, "18:00") == True


def test_calculate_available_hours():
    """Тест підрахунку доступних годин роботи"""
    outages = [
        {"start": "10:00", "end": "12:00"},
        {"start": "15:00", "end": "17:00"}
    ]
    
    scheduler = WorkScheduler()
    hours = scheduler.calculate_available_hours(outages, "09:00", "18:00")
    
    # 9-10 (1h) + 12-15 (3h) + 17-18 (1h) = 5h
    assert hours == 5.0

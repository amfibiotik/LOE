import pytest
from unittest.mock import Mock, AsyncMock
from src.bot import format_schedule, get_developer_info


def test_format_schedule():
    """Тест форматування графіку"""
    outages = [
        {"start": "08:00", "end": "11:00"},
        {"start": "14:00", "end": "17:00"}
    ]
    
    result = format_schedule(outages)
    assert "08:00-11:00" in result
    assert "14:00-17:00" in result


def test_format_schedule_empty():
    """Тест коли світло є"""
    result = format_schedule([])
    assert "✅" in result


def test_get_developer_info():
    """Тест інформації про розробника"""
    info = get_developer_info()
    assert "threads" in info.lower() or "розробник" in info.lower()

import pytest
from datetime import datetime
from src.parser import PowerScheduleParser


def test_parse_group_schedule():
    """Тест парсингу графіку для однієї групи"""
    html = """<p>Група 1.1. Електроенергії немає з 01:00 до 04:30, з 08:00 до 11:30.</p>"""
    
    parser = PowerScheduleParser()
    result = parser.parse_group_schedule(html, "1.1")
    
    assert result == [
        {"start": "01:00", "end": "04:30"},
        {"start": "08:00", "end": "11:30"}
    ]


def test_parse_group_no_outages():
    """Тест коли електроенергія є"""
    html = """<p>Група 3.1. Електроенергія є.</p>"""
    
    parser = PowerScheduleParser()
    result = parser.parse_group_schedule(html, "3.1")
    
    assert result == []


def test_parse_multiple_groups():
    """Тест парсингу кількох груп"""
    html = """
    <p>Група 1.1. Електроенергії немає з 01:00 до 04:30.</p>
    <p>Група 3.2. Електроенергії немає з 08:00 до 11:00, з 14:30 до 18:00.</p>
    """
    
    parser = PowerScheduleParser()
    result = parser.parse_all_groups(html)
    
    assert "1.1" in result
    assert "3.2" in result
    assert len(result["1.1"]) == 1
    assert len(result["3.2"]) == 2


def test_parse_date_from_html():
    """Тест витягування дати з HTML"""
    html = """<p><b>Графік погодинних відключень на 18.01.2026</b></p>"""
    
    parser = PowerScheduleParser()
    date = parser.extract_date(html)
    
    assert date == "18.01.2026"

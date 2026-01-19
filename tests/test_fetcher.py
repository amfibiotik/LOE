import pytest
from unittest.mock import Mock, patch
from src.fetcher import PowerDataFetcher


def test_fetch_schedule_success():
    """Тест успішного отримання даних"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hydra:member": [{
            "menuItems": [{
                "rawHtml": "<p>Група 1.1. Електроенергії немає з 08:00 до 11:00.</p>"
            }]
        }]
    }
    
    with patch('requests.get', return_value=mock_response):
        fetcher = PowerDataFetcher()
        result = fetcher.fetch_schedule()
        
        assert result is not None
        assert "rawHtml" in result


def test_fetch_schedule_network_error():
    """Тест обробки помилки мережі"""
    with patch('requests.get', side_effect=Exception("Network error")):
        fetcher = PowerDataFetcher()
        result = fetcher.fetch_schedule()
        
        assert result is None


def test_get_latest_schedule():
    """Тест отримання найсвіжішого графіку"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hydra:member": [{
            "menuItems": [
                {"id": 1, "name": "Today", "rawHtml": "<p>Графік</p>"},
                {"id": 2, "name": "Tomorrow", "rawHtml": ""},
            ]
        }]
    }
    
    with patch('requests.get', return_value=mock_response):
        fetcher = PowerDataFetcher()
        result = fetcher.get_latest_schedule()
        
        assert result["id"] == 1  # Повертає "Today" з HTML
        assert result["name"] == "Today"

import pytest
from unittest.mock import MagicMock

@pytest.fixture
def alert_config():
    config = MagicMock()
    config.alert.templates = {
        "expertise": """
        {% for event in events %}
        === Экспертиза {{ loop.index }} ===
        Название: {{ event.title }}
        {% if event.gpt %}
        Анализ:
        {% for key, value in event.gpt.items() %}
        - {{ key }}: {{ value }}
        {% endfor %}
        {% endif %}
        {% endfor %}
        """
    }
    return config

@pytest.fixture
def test_data():
    return {
        "events": [
            {
                "title": "Тест 1",
                "url": "http://test1.ru",
                "gpt": {
                    "объект": "Объект 1",
                    "адрес": "Адрес 1"
                }
            }
        ],
        "gpt_responses": {
            "events_0": {
                "объект": "Объект 1",
                "адрес": "Адрес 1"
            }
        }
    }
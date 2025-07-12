import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Настройка путей
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rostral.stages.alert import AlertStage

def test_alert_stage_output_format():
    """Тестирует ТОЛЬКО форматирование вывода в AlertStage"""
    # 1. Подготовка
    config = MagicMock()
    config.alert.templates = {
        "expertise": """{% for event in events %}
=== Экспертиза {{ loop.index }} ===
Название: {{ event.title }}
{% if event.gpt %}Анализ:{% for k,v in event.gpt.items() %}
- {{ k }}: {{ v }}{% endfor %}
{% else %}ℹ️ Нет данных{% endif %}
{% endfor %}"""
    }

    # 2. Тестовые данные
    test_data = {
        "events": [
            {
                "title": "Тестовая экспертиза 1",
                "gpt": {"Объект": "Тест1", "Адрес": "Адрес1"}
            },
            {
                "title": "Тестовая экспертиза 2",
                "gpt": None  # Нет данных
            }
        ]
    }

    # 3. Вызов
    alert = AlertStage(config)
    result = alert.run(test_data)
    output = result["alert"]["expertise"]

    # 4. Проверки
    print("\n=== ТЕСТИРУЕМ ТОЛЬКО ALERTSTAGE ===")
    print(output)

    # Проверяем форматирование
    assert "=== Экспертиза 1 ===" in output
    assert "Тестовая экспертиза 1" in output
    assert "- Объект: Тест1" in output
    assert "=== Экспертиза 2 ===" in output
    assert "ℹ️ Нет данных" in output

if __name__ == "__main__":
    test_alert_stage_output_format()
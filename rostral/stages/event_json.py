# rostral/stages/event_json.py

import requests
import json
import typer
from .base import PipelineStage
from typing import Dict, Any

class EventJsonStage(PipelineStage):
    """Стадия для загрузки и обновления JSON-данных событий"""
    
    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return data

        verify_ssl = getattr(self.config.source.fetch, "verify_ssl", True)
        headers = getattr(self.config.source.fetch, "headers", {}) or {}
        timeout = getattr(self.config.source.fetch, "timeout", 10)

        for block_name, items in data.items():
            if not isinstance(items, list):
                continue

            for record in items:
                url = record.get("url")
                if not url:  # Пропускаем если нет URL
                    continue

                try:
                    typer.echo(f"🌐 Загружаем детали из {url}")
                    response = requests.get(
                        url,
                        headers=headers,
                        verify=verify_ssl,
                        timeout=timeout
                    )
                    response.raise_for_status()

                    json_data = response.json()
                    
                    if json_data:
                        # Сохраняем имя шаблона перед обновлением
                        template_name = record.get("template_name", self.config.template_name)
                        
                        # Полностью перезаписываем поле text новыми данными
                        record["text"] = json.dumps(json_data, ensure_ascii=False, indent=2)
                        record["download_status"] = "json_success"
                        
                        # Гарантируем что template_name будет сохранен
                        record["template_name"] = template_name
                        typer.echo(f"✅ Текст события обновлен (шаблон: {template_name})")
                    else:
                        record["download_status"] = "json_empty"
                        typer.echo("⚠️ Получен пустой JSON-ответ")

                except json.JSONDecodeError:
                    record["download_status"] = "json_invalid"
                    typer.echo("❌ Ответ не является валидным JSON")
                except Exception as e:
                    record["download_status"] = "json_error"
                    typer.echo(f"❌ Ошибка загрузки JSON: {e}")

        return data
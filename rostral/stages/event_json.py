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
                    typer.echo(f"🌐 Loading details from {url}")
                    response = requests.get(
                        url,
                        headers=headers,
                        verify=verify_ssl,
                        timeout=timeout
                    )
                    response.raise_for_status()

                    json_data = response.json()
                    
                    if json_data:
                        
                        # Полностью перезаписываем поле text новыми данными
                        record["text"] = json.dumps(json_data, ensure_ascii=False, indent=2)
                        record["download_status"] = "json_success"
                        
                       
                        typer.echo(f"✅ Event text updated")
                    else:
                        record["download_status"] = "json_empty"
                        typer.echo("⚠️ Empty JSON response")

                except json.JSONDecodeError:
                    record["download_status"] = "json_invalid"
                    typer.echo("❌ Invalid JSON answer")
                except Exception as e:
                    record["download_status"] = "json_error"
                    typer.echo(f"❌ JSON loading error: {e}")

        return data
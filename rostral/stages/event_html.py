import requests
from bs4 import BeautifulSoup
from .base import PipelineStage
import typer

class EventHTMLStage(PipelineStage):
    def run(self, data):
        if not isinstance(data, dict):
            return data

        verify_ssl = getattr(self.config.source.fetch, "verify_ssl", True)
        headers = getattr(self.config.source.fetch, "headers", {}) or {}

        for block_name, items in data.items():
            if not isinstance(items, list):
                continue

            for record in items:
                url = record.get("url")
                if not url or record.get("page_text"):
                    continue  # Пропускаем, если уже есть текст

                try:
                    typer.echo(f"🌐 EventHTMLStage: loadind {url}")
                    response = requests.get(url, headers=headers, verify=verify_ssl, timeout=10)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, "html.parser")
                
                    selector = getattr(self.config.source.fetch, "selector", None)

                    if selector:
                        selected = soup.select(selector)
                        text = "\n".join([el.get_text(strip=True) for el in selected])
                    else:
                        text = soup.get_text(separator="\n", strip=True)


                    if text and len(text) > 50:
                        record["page_text"] = text
                        record["download_status"] = "html_success"
                        typer.echo(f"✅ Extracted {len(text)} HTML symbols")
                        record["text"] = record.get("text") or record.get("page_text") or record.get("doc_text")
                    else:
                        record["download_status"] = "html_empty"
                        typer.echo("⚠️ We've got empty or too short HTML response")

                except Exception as e:
                    record["download_status"] = "html_error"
                    record["page_text"] = None
                    typer.echo(f"❌ Error loading HTML: {e}")

        return data

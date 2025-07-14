# rostral/stages/fetch.py

import typer
import requests
import urllib3
from .base import PipelineStage        

# опционально, чтобы не видеть InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FetchStage(PipelineStage):
    def run(self, data):
        source = self.config.source
        url = self.render_url(source.url)
        headers = source.fetch.headers or {}
        verify = getattr(source.fetch, "verify_ssl", True)

        typer.echo(f"🔗 FetchStage: GET {url}  (verify_ssl={verify})")
        response = requests.get(
            url,
            headers=headers,
            timeout=source.fetch.timeout,
            verify=verify
        )
        typer.echo(f"📥 Ответ FetchStage: статус {response.status_code}")
        response.raise_for_status()

        if source.type == "html":
            return {"html": response.text}
        else:
            return {"json": response.json()}

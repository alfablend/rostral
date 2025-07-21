import requests
import time
import typer
from urllib.parse import urlparse
from typing import Optional, Dict, Any
from tqdm import tqdm
from .base import PipelineStage
from rostral.models import DownloadConfig
from rostral.stages.transforms import transform_smart_url
from rostral.db import is_known_by_hash, get_event_hash
from rostral.db import is_known_by_url 

class DownloadStage(PipelineStage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_retries = 3
        self.retry_delay = 2
        self.chunk_size = 1024 * 1024  # 1MB chunks

    def _is_pdf_url(self, url: str) -> bool:
        parsed = urlparse(url.lower())
        if parsed.path.endswith('.pdf'):
            return True
        # Для Яндекс.Диска считаем, что это PDF (но нужна дополнительная проверка в _download_file)
        if 'yandex.ru' in parsed.netloc or 'yadi.sk' in parsed.netloc:
            return True
        return False

    def _download_file(self, url: str, verify_ssl: bool) -> Optional[bytes]:
        """Загружает файл с обработкой ошибок"""
        time.sleep(0.5)
        source = self.config.source
        headers = source.fetch.headers or {}
        try:
            with requests.get(
                url,
                stream=True,
                timeout=self.config.download.timeout,
                verify=verify_ssl,
                headers=headers
            ) as response:
                response.raise_for_status()
                
                content = bytearray()
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        content.extend(chunk)
                
                if not content:
                    typer.echo("⚠️ Получен пустой файл")
                    return None
                    
                return bytes(content)
                
        except requests.exceptions.SSLError:
            typer.echo("⚠️ Ошибка SSL, пробуем без проверки")
            return self._download_file(url, verify_ssl=False)
        except Exception as e:
            typer.echo(f"❌ Ошибка загрузки: {e}")
            return None

    def _process_record(self, record: Dict[str, Any], verify_ssl: bool) -> bool:
        """Обрабатывает одну запись"""
        url = record.get("url_final") or record.get("url")
        if not url:
            return False

        # Преобразуем URL
        base_url = self.config.source.url.split('?')[0].split('#')[0] if self.config.source.url else None
        transformed_url = transform_smart_url(
            url,
            template_name=self.config.template_name,
            base_url=base_url
        )

        # Проверяем, нужно ли загружать
        if not self._is_pdf_url(transformed_url):
            typer.echo(f"⏭️ Пропущено: URL не распознан как PDF ({transformed_url})")
            return False

        # Пытаемся загрузить
        for attempt in range(self.max_retries):
            typer.echo(f"🔄 Попытка {attempt + 1} для {transformed_url}")
            content = self._download_file(transformed_url, verify_ssl)
            
            if content:
                record.update({
                    "file_content": content,
                    "download_status": "success",
                    "final_url": transformed_url
                })
                typer.echo(f"✅ Успешно загружено {len(content)} байт")
                return True
                
            time.sleep(self.retry_delay)
        
        record["download_error"] = f"Не удалось загрузить после {self.max_retries} попыток"
        return False

    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return data

        verify_ssl = getattr(self.config.source.fetch, "verify_ssl", True)
        stats = {"total": 0, "success": 0, "skipped": 0, "failed": 0}

        for block_name, items in data.items():
            if not isinstance(items, list):
                continue

            stats["total"] += len(items)
            processed_items = []

            for record in tqdm(items, desc=f"📥 Downloading [{block_name}]", unit="file"):
                if not isinstance(record, dict):
                    continue

                url = record.get("url_final") or record.get("url")
                if not url:
                    typer.echo("⚠️ Запись без URL — пропущена")
                    stats["skipped"] += 1
                    continue

                # ✅ Проверка по URL: если файл уже загружен — не качаем
                if is_known_by_url(url):
                    typer.echo(f"⏭️ Пропущено: файл уже загружался → {url}")
                    record["download_status"] = "skipped"
                    stats["skipped"] += 1
                    continue

                # 📦 Пытаемся загрузить
                if self._process_record(record, verify_ssl):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1

                processed_items.append(record)

            data[block_name] = processed_items

        typer.echo(f"\n📊 Итоги загрузки: загружено={stats['success']}, пропущено={stats['skipped']}, ошибки={stats['failed']}, всего={stats['total']}")
        return data
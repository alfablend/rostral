# rostral/stages/transforms.py

from typing import Optional
import requests
import urllib.parse
import time
from jinja2 import Template  # Добавляем импорт Jinja2
from rostral.cache import cached_transform

def transform_smart_url(url: str, *, template_name: Optional[str] = None, base_url: Optional[str] = None) -> str:
    """Универсальный трансформатор URL с поддержкой относительных путей и Яндекс.Диска"""
    if not url:
        return ""

    # Обработка относительных путей
    if url.startswith("/"):
        return urllib.parse.urljoin(base_url, url)
    
    # Обработка Яндекс.Диска
    if "yandex.ru" in url.lower() or "yadi.sk" in url.lower():
        return transform_yandex_disk(url)
    
    return url

@cached_transform("yandex_disk")
def transform_yandex_disk(url: str) -> str:
    """Простое и надёжное преобразование ссылок Яндекс.Диска"""
    try:
        if "downloader.disk.yandex.ru" in url:
            return url

        if "public_key=" in url:
            public_key = url.split("public_key=")[1].split("&")[0]
        elif "/d/" in url:
            public_key = url.split("/d/")[-1].split("?")[0].split("/")[0]
        elif "yadi.sk/d/" in url:
            public_key = url.split("yadi.sk/d/")[-1].split("?")[0].split("/")[0]
        else:
            return url

        api_url = f"https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key=https://disk.yandex.ru/d/{public_key}"

        response = requests.get(
            api_url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        
        response.raise_for_status()
        download_url = response.json().get("href", "")
        time.sleep(1)
        return download_url if download_url else url
    
    except Exception as e:
        print(f"⚠️ Yandex Disk link transformation error {url}: {str(e)}")
        return url



def transform_jinja(template_str: str, context: dict) -> str:
    from jinja2 import Template
    try:
        if not template_str:
            return ""
            
        # Если строка - просто имя переменной (без {{ }})
        if not any(c in template_str for c in ['{', '%']):
            return str(context.get(template_str, ""))
            
        return Template(template_str).render(**context)
    except Exception as e:
        print(f"Jinja2 error: {str(e)}")
        return "[RENDER_ERROR]"

TRANSFORM_REGISTRY = {
    "yandex_disk": transform_yandex_disk,
    "smart_url": transform_smart_url,
    "jinja": transform_jinja,  # Добавляем Jinja в реестр
}
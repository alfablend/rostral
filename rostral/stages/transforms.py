from typing import Optional
import requests
import urllib.parse
import time
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
        # Если это уже прямая ссылка для скачивания
        if "downloader.disk.yandex.ru" in url:
            return url

        # Извлекаем публичный ключ из URL
        if "public_key=" in url:
            public_key = url.split("public_key=")[1].split("&")[0]
        elif "/d/" in url:
            public_key = url.split("/d/")[-1].split("?")[0].split("/")[0]
        elif "yadi.sk/d/" in url:
            public_key = url.split("yadi.sk/d/")[-1].split("?")[0].split("/")[0]
        else:
            return url  # Неизвестный формат ссылки

        # Получаем прямую ссылку через API
        api_url = f"https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key=https://disk.yandex.ru/d/{public_key}"

        response = requests.get(
            api_url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        
        response.raise_for_status()
        
        download_url = response.json().get("href", "")
        
        return download_url if download_url else url
    
        time.sleep(1)
            
    except Exception as e:
        print(f"⚠️ Ошибка преобразования ссылки Яндекс.Диска {url}: {str(e)}")
        return url


TRANSFORM_REGISTRY = {
    "yandex_disk": transform_yandex_disk,
    "smart_url": transform_smart_url,
}
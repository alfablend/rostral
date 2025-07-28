from sqlalchemy import create_engine, exists
from sqlalchemy.orm import sessionmaker
from .models import Base, Event
from datetime import datetime, timezone
import hashlib

engine = create_engine("sqlite:///rostral_cache.db")
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

def get_event_hash(record: dict) -> str:
    """
    Универсальный хэш для любой системы:
    - Использует **url** (обязательно) + **title** (если есть)  
    - Если title нет → только url  
    - Усекает длинные title до 200 символов (чтобы хэш не ломался)  
    """
    url = record.get("url", "")
    if not url:
        raise ValueError("URL is required for hashing")

    title_part = (record.get("title", "")[:200]).strip()  # Обрезаем слишком длинные заголовки
    composite = (url + title_part).lower().encode("utf-8")
    return hashlib.md5(composite).hexdigest()

def is_known_by_hash(record: dict) -> bool:
    """Проверяет, есть ли уже событие с таким хэшем в БД"""
    session = Session()
    try:
        event_hash = get_event_hash(record)
        exists = session.query(Event).filter_by(event_id=event_hash).first() is not None
        return exists
    finally:
        session.close()

def is_known_by_url(url: str) -> bool:
    """Проверяет, есть ли уже событие с таким URL в БД"""
    if not url:
        return False

    session = Session()
    try:
        return session.query(exists().where(Event.url == url)).scalar()
    finally:
        session.close()

def save_event(record: dict, **kwargs) -> bool:
    """
    Сохраняет событие в базу данных.
    Параметры:
    - record: словарь с данными события (обязательно должен содержать 'url')
    - **kwargs: игнорирует лишние параметры (например, config) для совместимости
    """
    session = Session()
    try:
        url = record.get("url")
        if not url:
            raise ValueError("URL is required")

        # Проверяем дубликаты
        if is_known_by_url(url) or is_known_by_hash(record):
            return False

        event = Event(
            event_id=get_event_hash(record),
            url=url,
            title=record.get("title", "")[:500],
            text=record.get("text", ""),
            excerpt=record.get("excerpt", ""),
            gpt_text=record.get("gpt_text"),
            error=record.get("error"),
            status=record.get("status", "pending"),
            template_name=record.get("template_name")  # Берем из record, если есть
        )
        
        session.add(event)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        typer.echo(f"❌ Ошибка сохранения: {str(e)}", err=True)
        return False
    finally:
        session.close()
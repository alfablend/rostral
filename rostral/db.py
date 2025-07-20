from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Event 
from datetime import datetime, timezone
import hashlib

engine = create_engine("sqlite:///rostral_cache.db")

# Создаём фабрику сессий
Session = sessionmaker(bind=engine)

# Инициализируем все таблицы из Base (включая Event)
Base.metadata.create_all(engine)

import hashlib

def get_event_hash(record: dict) -> str:
    composite = (record.get("title", "") + record.get("text", "")).strip().lower()
    return hashlib.md5(composite.encode("utf-8")).hexdigest()


def is_known_by_hash(record: dict) -> bool:
    event_hash = get_event_hash(record)
    session = Session()
    exists = session.query(Event).filter_by(event_id=event_hash).first()
    session.close()
    return exists is not None



def save_event(record: dict):
    session = Session()

    if is_known_by_hash(record):
        session.close()
        return
    event_id = get_event_hash(record)
    title = record.get("title", "")
    text = record.get("text", "")
    event = Event(
        event_id=event_id,
        url=record.get("final_url", record["url"]),
        title=title,
        text=text,
        excerpt=record.get("excerpt"),
        gpt_text=record.get("gpt_text"),
        error=record.get("error"),
        status=record.get("status", "pending"),
        timestamp=record.get("timestamp", datetime.now(timezone.utc)),
    )
    session.add(event)
    session.commit()
    session.close()



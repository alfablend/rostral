from pydantic import BaseModel, HttpUrl
from typing import Any, Dict, List, Optional, Union
import yaml
from pathlib import Path
from sqlalchemy import Column, String, Float, Integer, Text, DateTime
from datetime import datetime, timezone
from sqlalchemy.ext.declarative import declarative_base

class DownloadConfig(BaseModel):
    """
    Configuration for DownloadStage:
      - extensions: list of file suffixes to download (e.g. ['.pdf', '.docx'])
      - timeout: HTTP request timeout in seconds
    """
    extensions: List[str] = [".pdf", ".docx"]
    timeout: int = 20
    allow_html: bool = False

class FetchConfig(BaseModel):
    headers: Dict[str, str] = {}
    retry_policy: Dict[str, Any]
    timeout: int = 10
    verify_ssl: bool = True


class SourceConfig(BaseModel):
    type: str
    url: str
    endpoints: Optional[Dict[str, str]] = None
    frequency: str
    fetch: FetchConfig


class ExtractFieldConfig(BaseModel):
    attr: Optional[str] = None
    transform: Optional[str] = None
    transform_type: Optional[str] = None


class ExtractItemConfig(BaseModel):
    selector: str
    type: str
    fields: Dict[str, Union[ExtractFieldConfig, str]]
    limit: Optional[int] = None

class FilterRule(BaseModel):
    unique: Optional[str] = None
    filter: Optional[str] = None
    condition: Optional[str] = None


class NormalizeRule(BaseModel):
    field: str
    filters: List[FilterRule]


class NormalizeConfig(BaseModel):
    rules: List[NormalizeRule]


class ProcessingConfig(BaseModel):  
    extract_keywords: List[str] = []


class GPTConfig(BaseModel):
    prompt: str


class AlertConfig(BaseModel):
    templates: Dict[str, str]
    rules: Optional[Any] = None


class TestEvent(BaseModel):
    url: HttpUrl
    note: Optional[str] = None


class Config(BaseModel):
    version: int
    meta: Dict[str, Any]
    source: SourceConfig
    template_name: str 
   
    download: DownloadConfig = DownloadConfig()

    extract: Optional[Dict[str, ExtractItemConfig]] = None
    normalize: Optional[NormalizeConfig] = None     
    processing: Optional[ProcessingConfig] = None
    gpt: Optional[GPTConfig] = None     
    alert: Optional[AlertConfig] = None

    test_event: Optional[TestEvent] = None
    secrets: Optional[Dict[str, Any]] = None
    

def load_yaml_config(path: str) -> Config:
    """
    Load a YAML template from `path`, parse into a Config object.
    Uses Pydantic v2 `model_validate`.
    """
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    return Config.model_validate(data)


# SQLAlchemy models (unique from the second file)
Base = declarative_base()

class TransformCache(Base):
    __tablename__ = "transform_cache"

    template_name = Column(String, primary_key=True)
    transform_name = Column(String, primary_key=True)
    input = Column(String, primary_key=True)
    output = Column(String)
    updated_at = Column(Float)

timestamp = datetime.now(timezone.utc)
class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True)
    url = Column(String, unique=True)
    title = Column(String(500))
    text = Column(Text)
    excerpt = Column(Text)
    gpt_text = Column(Text)
    error = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    template_name = Column(String) 
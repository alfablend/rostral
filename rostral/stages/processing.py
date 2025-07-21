import os
import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, List
import typer
from .base import PipelineStage
from rostral.db import get_event_hash, is_known_by_hash

MAX_FRAGMENT_LENGTH = int(os.getenv("GPT_FRAGMENT_MAX_LENGTH", 200))
TEXT_MAX_LENGTH = int(os.getenv("GPT_TEXT_MAX_LENGTH", 2000))
CHUNK_HEAD = int(os.getenv("GPT_CHUNK_HEAD", TEXT_MAX_LENGTH // 2))
CHUNK_TAIL = int(os.getenv("GPT_CHUNK_TAIL", TEXT_MAX_LENGTH // 2))

def extract_text_fragments(text: str, keywords: List[str],
                         max_fragment_length=MAX_FRAGMENT_LENGTH,
                         total_max_length=TEXT_MAX_LENGTH) -> str:
    if not text or not keywords:
        return text[:total_max_length] if text else ""
    
    fragments = []
    lower_text = text.lower()
    lower_keywords = [kw.lower() for kw in keywords]
    
    for kw in lower_keywords:
        idx = lower_text.find(kw)
        if idx == -1:
            continue

        start = max(0, idx - max_fragment_length // 2)
        end = min(len(text), idx + len(kw) + max_fragment_length // 2)

        fragment = text[start:end].strip()
        if fragment not in fragments:  # Избегаем дубликатов
            fragments.append(fragment)

    if not fragments:
        return text[:total_max_length] if text else ""
        
    excerpt = " [...] ".join(fragments)
    if len(excerpt) > total_max_length:
        return excerpt[:CHUNK_HEAD] + " [...] " + excerpt[-CHUNK_TAIL:]
    return excerpt

class ProcessingStage(PipelineStage):
    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        processing_meta = {
            "timestamp": datetime.now().isoformat(),
            "processed_files": 0,
            "errors": []
        }

        typer.echo(f"⚙️ ProcessingStage input data: {type(data)}")
        typer.echo(f"📐 ENV limits: fragment={MAX_FRAGMENT_LENGTH}, gpt_text={TEXT_MAX_LENGTH}, head={CHUNK_HEAD}, tail={CHUNK_TAIL}")

        if not isinstance(data, dict):
            typer.echo("ℹ️ Input data is not a dictionary, skipping processing")
            return data

        for block_name, items in data.items():
            if not isinstance(items, list):
                typer.echo(f"🔸 Skipping block '{block_name}' (not a list)")
                continue

            typer.echo(f"🔧 Processing block '{block_name}' with {len(items)} items")
            data[block_name] = [r for r in items if self._process_record(r, processing_meta)]

        data["__processing__"] = processing_meta
        typer.echo(f"✅ Processed {processing_meta['processed_files']} PDF files")

        if "events" in data:
            for i, event in enumerate(data["events"]):
                typer.echo(f"📄 Документ #{i+1}: {event.get('title', 'Без названия')}")
                
        else:
            typer.echo("❌ 'events' отсутствует")

        return data

    def _process_record(self, record: Dict[str, Any], meta: Dict[str, Any]) -> bool:
        if not record.get("file_content") or ".pdf" not in record.get("url", "").lower():
            typer.echo("❌ Файл не PDF, пропуск")
            return False

        try:
            text = self._extract_pdf_text(record["file_content"])
            record["text"] = text
            record["event_id"] = get_event_hash(record)

            if is_known_by_hash(record):
                typer.echo(f"⏭️ Пропуск: уже было → {record['url']}")
                return False

            del record["file_content"]
            meta["processed_files"] += 1
            typer.echo(f"📝 Extracted text from PDF ({len(text)} chars)")
        except Exception as e:
            error_msg = f"Failed to process PDF: {str(e)}"
            record["text"] = f"[ERROR: {error_msg}]"
            record["error"] = error_msg
            meta["errors"].append({
                "url": record.get("url", "unknown"),
                "error": error_msg
            })
            typer.echo(f"❌ {error_msg}")
            return False

        keywords = getattr(self.config.processing, "extract_keywords", [])
    
        if keywords:
            excerpt = extract_text_fragments(text, keywords)

            record["excerpt"] = excerpt
            if not excerpt.strip():
                typer.echo(f"⚠️ Ключевые слова не найдены в тексте → {record.get('url')}")
            record["gpt_text"] = excerpt
            typer.echo(f"🔍 excerpt by keywords → {len(excerpt)} chars")
            typer.echo(f"✂️ gpt_text set to excerpt ({len(excerpt)} chars)")
        else:
            if len(text) > TEXT_MAX_LENGTH:
                record["gpt_text"] = f"{text[:CHUNK_HEAD]} ... {text[-CHUNK_TAIL:]}"
                typer.echo(f"✂️ gpt_text trimmed from full text to {len(record['gpt_text'])} chars")
            else:
                record["gpt_text"] = text

        return True

    def _extract_pdf_text(self, pdf_content: bytes, max_pages: int = 10) -> str:
        text_parts = []
        doc = fitz.open(stream=BytesIO(pdf_content), filetype="pdf")
        for page_num in range(min(len(doc), max_pages)):
            page = doc.load_page(page_num)
            text = self._extract_page_text(page)
            if text:
                text_parts.append(text)
        return "\n".join(text_parts).strip()

    def _extract_page_text(self, page) -> str:
        text = page.get_text().strip()
        if text:
            return text
        try:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return pytesseract.image_to_string(img, lang="rus+eng").strip()
        except Exception as e:
            return f"[OCR failed: {str(e)}]"

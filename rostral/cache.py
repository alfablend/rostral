# rostral/cache.py

from rostral.db import Session
from rostral.models import TransformCache
import time

def get_from_cache(template, transform, input_value):
    session = Session()
    row = session.query(TransformCache).filter_by(
        template_name=template,
        transform_name=transform,
        input=input_value
    ).first()
    session.close()
    return row.output if row else None

def save_to_cache(template, transform, input_value, output_value):
    session = Session()
    row = TransformCache(
        template_name=template,
        transform_name=transform,
        input=input_value,
        output=output_value,
        updated_at=time.time()
    )
    session.merge(row)
    session.commit()
    session.close()

def cached_transform(transform_name: str):
    def decorator(func):
        def wrapper(input_value: str, **kwargs):
            template_name = kwargs.get("template_name")
            if not template_name:
                raise ValueError("Missing required keyword argument: template_name")

            cached = get_from_cache(template_name, transform_name, input_value)
            if cached:
                return cached

            result = func(input_value, **kwargs)
            save_to_cache(template_name, transform_name, input_value, result)
            return result
        return wrapper
    return decorator
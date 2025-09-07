import json
import math
import builtins
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
from typing import Callable, Any
from pydantic import BaseModel
from decimal import Decimal
 

def composite_review(reviews: list[str]):
    composite = ""
    template = "Review №{number}"

    for i, review in enumerate(reviews):
        composite += template.format(number=i+1)
        composite += review
        composite += "\n"
    return composite


def aggregate(schema: BaseModel, functions: Callable[[float], Any] | str) -> dict[str, Any]:
    data = schema.model_dump() if hasattr(schema, "model_dump") else schema.dict()
    if callable(functions):
        func = functions
    elif isinstance(functions, str):
        func = getattr(np, functions, None) or getattr(math, functions, None) or getattr(builtins, functions, None)
        if not callable(func):
            raise ValueError(f"function '{functions}' not found or not callable")
    else:
        raise TypeError("functions must be a callable or a function name (str)")
    
    out= {}
    for k, v in data.items():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float, Decimal, np.integer, np.floating)):
            out[k] = func(v)
    return out
 

def remove_ambiguous_sides(json_text: str) -> str:
    data = json.loads(json_text)
    sides = data.get('sides')

    if isinstance(sides, list):
        def is_ambiguous(item: dict) -> bool:
            if not isinstance(item, dict):
                return False
            v = item.get('kind', item.get('king'))
            return isinstance(v, str) and v.strip().lower() == 'ambiguous'

        data['sides'] = [item for item in sides if not is_ambiguous(item)]

    return json.dumps(data, ensure_ascii=False)


def get_provider(base_url: str):
    if 'openrouter' in base_url:
        return 'openrouter'
    if 'openai' in base_url:
        return 'openai'
    if 'localhost' in base_url:
        return 'local'
    raise ValueError(
        f"Unable to determine provider from base_url: {base_url!r}. "
        "Expected it to contain 'openrouter', 'openai', or 'localhost'."
    )

def get_client():
    load_dotenv()
    return OpenAI()
from typing import Literal
from openai import OpenAI
from pydantic import BaseModel


def get_so_completion(
    log: list,
    model_name: str,
    client: OpenAI,
    pydantic_model: BaseModel,
    provider_name: Literal['openai', 'openrouter', 'local'],
):
    job = None
    if provider_name == 'openai':
        completion = client.beta.chat.completions.parse(
            model=model_name,
            response_format=pydantic_model,
            messages=log,
            max_completion_tokens=10000,
        )
        job = completion.choices[0].message.parsed
    elif provider_name == 'openrouter' or provider_name == "local":
        model_schema = pydantic_model.model_json_schema()
        completion = client.chat.completions.create(
            model=model_name,
            messages=log,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": pydantic_model.__name__,
                    "schema": model_schema
                }
            },
            temperature=0.0
        )
        job = completion.choices[0].message.content
    else:
        raise ValueError(
            f"Unsupported provider_name: {provider_name!r}. "
            "Supported providers are: 'openai', 'openrouter', 'local'."
        )
    
    if job is None:
        raise RuntimeError(
            f"Completion returned no result for provider {provider_name!r} "
            f"and model {model_name!r}. This typically indicates an empty API response "
            "or a parsing/formatting issue."
        )
    return job


# да, это можно было смердижть с get_so_completion - мне пока лень
def get_default_completion(
    log: list,
    model_name: str,
    client: OpenAI
):
    completion = client.chat.completions.create(
        model=model_name,
        messages=log,
    )
    job = completion.choices[0].message.content
    if job is None:
        raise RuntimeError(
            f"Completion returned no result for model {model_name!r}. "
            "This typically indicates an empty API response "
            "or a parsing/formatting issue."
        )
    return job
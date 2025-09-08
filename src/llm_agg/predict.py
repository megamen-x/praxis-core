import os
from src.llm_agg.response import (
    get_default_completion,
    get_so_completion,
)
from src.llm_agg.utils import (
    remove_ambiguous_sides,
    get_provider,
)
from src.llm_agg.schemas.sides import Sides
from src.llm_agg.schemas.recommendations import Recommendations
from src.llm_agg.prompts.base import BASE_PROMPT_WO_TASK
from src.llm_agg.prompts.eval import RECOMMENDATIONS_PROMPT as REC_PROMPT


def user_feedback_agg(
    client,
    model_name: str,
    composite_review: str,
    SIDES_EXTRACTING_PROMPT: str,
    provider: str | None = None,
    RECOMMENDATIONS_PROMPT: str | None = REC_PROMPT,
    SYSTEM_PROMPT: str | None = BASE_PROMPT_WO_TASK
) -> tuple:
    if provider is None:
        provider = get_provider(os.getenv("OPENAI_BASE_URL"))

    log = []
    if SYSTEM_PROMPT is not None:
        log.append({
            "role": "system",
            "content": SYSTEM_PROMPT
        })
    log.append({
        "role": "user",
        "content": SIDES_EXTRACTING_PROMPT.format(feedback=composite_review)
    })

    user_analytics = get_so_completion(
        log=log,
        model_name=model_name,
        client=client,
        pydantic_model=Sides,
        provider_name=provider
    )

    if RECOMMENDATIONS_PROMPT is not None:
        log.append({
            "role":"assistant",
            "content": remove_ambiguous_sides(user_analytics)
        })
        log.append({
            "role":"user",
            "content": RECOMMENDATIONS_PROMPT
        })

        recs = get_so_completion(
            log=log,
            model_name=model_name,
            client=client,
            pydantic_model=Recommendations,
            provider_name=provider
        )

        return user_analytics, recs
    return user_analytics, None
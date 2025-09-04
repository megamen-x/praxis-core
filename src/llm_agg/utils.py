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
    
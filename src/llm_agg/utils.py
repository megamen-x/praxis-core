def get_provider(base_url: str):
    if 'openrouter' in base_url:
        return 'openrouter'
    if 'openai' in base_url:
        return 'openai'
    if 'localhost' in base_url:
        return 'local'
    raise 
    
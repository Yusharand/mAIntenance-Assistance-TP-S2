
import os

_client = None
_client_init_tried = False


def _get_client():
    global _client, _client_init_tried
    if _client_init_tried:
        return _client
    _client_init_tried = True

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq
        _client = Groq(api_key=api_key)
    except Exception:
        _client = None
    return _client


def call_llm(prompt: str, system: str | None = None, temperature: float = 0.3,
             max_tokens: int = 500) -> str | None:
    """Appelle Groq avec un prompt utilisateur (+ message système optionnel).
    Retourne None en cas d'échec (clé absente, réseau, erreur API) — ne lève
    jamais d'exception, pour que les appelants puissent toujours retomber sur
    un comportement dégradé prévisible."""
    client = _get_client()
    if client is None:
        return None

    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception:
        return None


def is_llm_available() -> bool:
    return _get_client() is not None

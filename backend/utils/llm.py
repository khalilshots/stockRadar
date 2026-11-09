import json
import logging
import re

from pydantic import BaseModel, ValidationError

from config.settings import settings

logger = logging.getLogger(__name__)

# once the model fails (ollama not running, model not pulled) we stop calling it
# for the rest of the scan instead of waiting on a timeout for every ticker
_unavailable = False


def reset() -> None:
    global _unavailable
    _unavailable = False


def available() -> bool:
    return settings.llm_enabled and not _unavailable


def extract_json(text: str) -> dict | None:
    """Pull the first json object out of a reply, even if the model wrapped it in prose or fences."""
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def ask(system: str, user: str, schema: type[BaseModel]) -> BaseModel | None:
    """
    Send one prompt and validate the reply against a pydantic schema.
    Returns None on any failure so the caller can fall back to its rules.
    """
    global _unavailable
    if not available():
        return None

    import litellm

    # skip params a provider doesn't support instead of erroring
    litellm.drop_params = True
    litellm.suppress_debug_info = True

    try:
        response = litellm.completion(
            model=settings.llm_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
    except Exception as e:
        logger.warning(f"llm call failed, using rules for the rest of this scan: {type(e).__name__}: {e}")
        _unavailable = True
        return None

    data = extract_json(raw)
    if data is None:
        logger.info(f"llm reply wasn't json: {raw[:120]!r}")
        return None
    try:
        return schema.model_validate(data)
    except ValidationError:
        logger.info(f"llm reply didn't match {schema.__name__}: {data}")
        return None

import logging
import time
from typing import Any

from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from app.config import settings

logger = logging.getLogger(__name__)

_RETRY_STATUSES = {429, 503}
_MAX_RETRIES = 4


class LLMUnavailable(RuntimeError):
    """Raised when the LLM path cannot be used."""
    pass


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is not None:
        return _client

    if not settings.llm_configured:
        raise LLMUnavailable("GEMINI_API_KEY is not configured")

    try:
        _client = genai.Client(api_key=settings.gemini_api_key)
    except Exception as exc:
        raise LLMUnavailable(f"Failed to initialize Gemini client: {exc}") from exc
    return _client


def is_available() -> bool:
    return settings.llm_configured


def parse(system: str, user: str, schema: type[BaseModel]) -> tuple[BaseModel, int]:
    """One structured-output request with retry on 429/503. Returns (parsed, tokens_used)."""
    client = _get_client()

    last_exc: Exception | None = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.llm_model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.2,
                ),
            )
            break  # success
        except (ClientError, ServerError) as exc:
            status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            err_msg = str(exc)

            # Check for daily quota exhaustion vs temporary rate limit
            is_daily_quota = False
            if status == 429:
                if "Quota exceeded" in err_msg and ("free_tier_requests" in err_msg or "GenerateRequestsPerDay" in err_msg or "limit: 20" in err_msg):
                    is_daily_quota = True

            if is_daily_quota:
                logger.error(f"Daily quota exhaustion: {exc}")
                raise LLMUnavailable("Gemini daily free-tier quota has been reached. Please try again later or switch to a project/model with available quota.") from exc

            if status in {429, 503} and attempt < max_retries - 1:
                wait = 10 * (2 ** attempt)  # exponential backoff: 10s, 20s
                reason = "rate limit" if status == 429 else "temporary service error"
                logger.warning(
                    f"Gemini API {status} ({reason}) on attempt {attempt + 1}/{max_retries}, "
                    f"retrying in {wait}s... ({exc})"
                )
                time.sleep(wait)
                last_exc = exc
                continue
            
            logger.error(f"Gemini API error (status {status}): {exc}")
            raise LLMUnavailable(f"Gemini API error: {exc}") from exc
        except Exception as exc:
            logger.error(f"Gemini API error: {exc}")
            raise LLMUnavailable(f"Gemini API error: {exc}") from exc
    else:
        raise LLMUnavailable(f"Gemini API failed after {max_retries} retries: {last_exc}") from last_exc

    if not response.text:
        raise LLMUnavailable("Model returned no output")

    try:
        parsed = schema.model_validate_json(response.text)
    except Exception as exc:
        logger.error(f"Failed to parse Gemini output into schema: {exc}\nRaw output: {response.text}")
        raise LLMUnavailable("Model returned output that could not be parsed as the requested schema") from exc

    usage = getattr(response, "usage_metadata", None)
    tokens = 0
    if usage is not None:
        tokens = (getattr(usage, "prompt_token_count", 0) or 0) + (getattr(usage, "candidates_token_count", 0) or 0)

    return parsed, tokens

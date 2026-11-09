import logging

import requests

from utils import cache, rate_limiter

logger = logging.getLogger(__name__)


class SourceUnavailable(Exception):
    """The api has no key, is out of budget, or returned an error."""


def get_json(api: str, url: str, params: dict, cache_key: str, ttl: int, secret_param: str):
    """
    GET a json api with caching and rate limiting.
    cache_key must not include the api key, and secret_param is never logged.
    """
    cached = cache.read(api, cache_key, ttl)
    if cached is not None:
        return cached

    if not params.get(secret_param):
        raise SourceUnavailable(f"{api}: no api key set")

    if not rate_limiter.acquire(api):
        raise SourceUnavailable(f"{api}: daily limit reached")

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        # the exception text can contain the full url with the key in it
        logger.warning(f"{api} request failed ({type(e).__name__}) for {cache_key}")
        raise SourceUnavailable(f"{api}: request failed") from e

    cache.write(api, cache_key, data)
    return data

import pytest

import api
from guards import RateLimiter


@pytest.fixture(autouse=True)
def generous_rate_limit():
    """Most tests call the AI endpoints many times. The rate-limit tests set their own."""
    original = api.limiter
    api.limiter = RateLimiter(per_client=10_000, overall=10_000)
    yield
    api.limiter = original

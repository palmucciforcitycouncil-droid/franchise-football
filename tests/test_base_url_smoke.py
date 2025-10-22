from tests.utils.api_base import api
import requests

def test_health_uses_consistent_base():
    url = f"{api()}/diag/health"
    r = requests.get(url, timeout=3)
    assert r.ok, f"Health failed for {url}"

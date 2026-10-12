from urllib.parse import parse_qs

import httpx
import pytest

from app.opensky.auth import TOKEN_URL, TokenError, TokenManager


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class FakeTokenServer:
    """Stands in for the OpenSky token endpoint and records what it was sent."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.response = lambda n: httpx.Response(
            200, json={"access_token": f"token-{n}", "expires_in": 1800}
        )

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        result = self.response(len(self.requests))
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def server() -> FakeTokenServer:
    return FakeTokenServer()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def manager(server: FakeTokenServer, clock: FakeClock) -> TokenManager:
    http = httpx.Client(transport=httpx.MockTransport(server))
    return TokenManager("my-client", "my-secret", http, clock=clock)


def test_requests_token_with_client_credentials(
    manager: TokenManager, server: FakeTokenServer
) -> None:
    assert manager.get_token() == "token-1"

    request = server.requests[0]
    assert request.method == "POST"
    assert str(request.url) == TOKEN_URL
    assert parse_qs(request.content.decode()) == {
        "grant_type": ["client_credentials"],
        "client_id": ["my-client"],
        "client_secret": ["my-secret"],
    }


def test_token_is_reused_until_shortly_before_expiry(
    manager: TokenManager, server: FakeTokenServer, clock: FakeClock
) -> None:
    manager.get_token()

    clock.now += 1769  # one second before the 30 s refresh margin
    assert manager.get_token() == "token-1"
    assert len(server.requests) == 1

    clock.now += 1
    assert manager.get_token() == "token-2"
    assert len(server.requests) == 2


def test_invalidate_forces_a_new_token(manager: TokenManager, server: FakeTokenServer) -> None:
    manager.get_token()
    manager.invalidate()

    assert manager.get_token() == "token-2"


def test_missing_expires_in_falls_back_to_documented_lifetime(
    manager: TokenManager, server: FakeTokenServer, clock: FakeClock
) -> None:
    server.response = lambda n: httpx.Response(200, json={"access_token": f"token-{n}"})
    manager.get_token()

    clock.now += 1769
    assert manager.get_token() == "token-1"
    clock.now += 1
    assert manager.get_token() == "token-2"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, json={"error": "invalid_client"}),
        httpx.Response(503, text="unavailable"),
        httpx.Response(200, text="<html>not json</html>"),
        httpx.Response(200, json={"expires_in": 1800}),
        httpx.Response(200, json={"access_token": ""}),
        httpx.Response(200, json=["unexpected"]),
        httpx.ConnectTimeout("timed out"),
    ],
    ids=["401", "503", "not-json", "no-token", "empty-token", "wrong-shape", "timeout"],
)
def test_failures_raise_token_error_without_leaking_the_secret(
    manager: TokenManager, server: FakeTokenServer, response: httpx.Response | Exception
) -> None:
    server.response = lambda n: response

    with pytest.raises(TokenError) as excinfo:
        manager.get_token()

    assert "my-secret" not in str(excinfo.value)


def test_recovers_after_a_failed_fetch(manager: TokenManager, server: FakeTokenServer) -> None:
    good = server.response
    server.response = lambda n: httpx.Response(503)
    with pytest.raises(TokenError):
        manager.get_token()

    server.response = good
    assert manager.get_token() == "token-2"

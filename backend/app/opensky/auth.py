"""OAuth2 client-credentials tokens for the OpenSky API.

OpenSky stopped accepting username/password in March 2026. A client ID and secret
are exchanged for a bearer token that lasts about 30 minutes, so anything that runs
longer than that has to refresh it.
"""

import time
from collections.abc import Callable

import httpx

TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
)
# Refresh this long before expiry so a token never expires mid-request.
REFRESH_MARGIN_S = 30
# Used if the token response omits expires_in. Matches the documented lifetime.
DEFAULT_EXPIRES_IN_S = 1800


class TokenError(Exception):
    """A token could not be obtained. The message never contains the client secret."""


class TokenManager:
    """Hands out a valid bearer token, fetching a new one only when needed."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        http: httpx.Client,
        *,
        token_url: str = TOKEN_URL,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http
        self._token_url = token_url
        self._clock = clock
        self._token: str | None = None
        self._refresh_at = 0.0

    def get_token(self) -> str:
        if self._token is None or self._clock() >= self._refresh_at:
            self._fetch()
        return self._token

    def invalidate(self) -> None:
        """Forget the current token. Call after a 401 so the next request fetches a new one."""
        self._token = None

    def _fetch(self) -> None:
        try:
            response = self._http.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
        except httpx.HTTPError as exc:
            raise TokenError(f"token request failed: {type(exc).__name__}") from exc

        if response.status_code != 200:
            raise TokenError(f"token endpoint returned HTTP {response.status_code}")

        try:
            payload = response.json()
            token = payload["access_token"]
            expires_in = float(payload.get("expires_in", DEFAULT_EXPIRES_IN_S))
        except (ValueError, KeyError, TypeError) as exc:
            raise TokenError("token endpoint returned an unexpected body") from exc
        if not isinstance(token, str) or not token:
            raise TokenError("token endpoint returned an unexpected body")

        self._token = token
        self._refresh_at = self._clock() + max(expires_in - REFRESH_MARGIN_S, 0)

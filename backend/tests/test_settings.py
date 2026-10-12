import pytest
from pydantic import ValidationError

from app.settings import Settings


def make_settings(**overrides) -> Settings:
    # _env_file=None keeps the developer's real .env out of the tests.
    return Settings(_env_file=None, **overrides)


def test_defaults_are_anonymous_and_florida(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("OPENSKY_CLIENT_ID", "OPENSKY_CLIENT_SECRET"):
        monkeypatch.delenv(name, raising=False)

    settings = make_settings()

    assert settings.opensky_client_id is None
    assert settings.opensky_client_secret is None
    assert (settings.bbox_lamin, settings.bbox_lamax) == (24.3, 31.1)
    assert (settings.bbox_lomin, settings.bbox_lomax) == (-87.7, -79.8)


def test_blank_credentials_mean_anonymous() -> None:
    settings = make_settings(opensky_client_id="", opensky_client_secret="")

    assert settings.opensky_client_id is None
    assert settings.opensky_client_secret is None


def test_secret_is_not_shown_in_repr() -> None:
    settings = make_settings(opensky_client_id="me", opensky_client_secret="hunter2")

    assert "hunter2" not in repr(settings)
    assert settings.opensky_client_secret.get_secret_value() == "hunter2"


def test_half_configured_credentials_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENSKY_CLIENT_SECRET", raising=False)

    with pytest.raises(ValidationError, match="both"):
        make_settings(opensky_client_id="me")


@pytest.mark.parametrize(
    "overrides",
    [
        {"bbox_lamin": 31.1, "bbox_lamax": 24.3},
        {"bbox_lomin": -79.8, "bbox_lomax": -87.7},
        {"bbox_lamax": 91.0},
    ],
)
def test_invalid_bounding_box_is_rejected(overrides: dict) -> None:
    with pytest.raises(ValidationError, match="bounding box"):
        make_settings(**overrides)

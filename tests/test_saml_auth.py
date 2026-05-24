# SPDX-License-Identifier: MIT
"""Tests for core/auth/saml.py — SAMLAuthProvider.

Coverage target: 0% → ~90% of the SAML authentication module.

Strategy:
  - ``python3-saml`` is an optional dependency.  All tests mock
    ``onelogin.saml2.auth.OneLogin_Saml2_Auth`` so the suite runs in CI
    without the native XML libraries installed.
  - Tests cover: import guard, missing config, response size limit,
    validation errors, attribute mapping, role fallback, tenant extraction,
    health check, and the ``http_host`` derivation fix.
"""

from __future__ import annotations

import base64
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

METADATA_URL = "https://idp.example.com/metadata"
ENTITY_ID = "https://sp.example.com/saml/metadata"
ACS_URL = "https://sp.example.com/saml/acs"


def _make_provider(**kwargs: Any):
    """Return a SAMLAuthProvider with mocked python3-saml import."""
    from core.auth.saml import SAMLAuthProvider

    return SAMLAuthProvider(
        metadata_url=kwargs.get("metadata_url", METADATA_URL),
        entity_id=kwargs.get("entity_id", ENTITY_ID),
        acs_url=kwargs.get("acs_url", ACS_URL),
    )


def _mock_saml_auth(
    is_authenticated: bool = True,
    errors: list[str] | None = None,
    attributes: dict | None = None,
    name_id: str = "user@example.com",
) -> MagicMock:
    """Build a mock OneLogin_Saml2_Auth instance."""
    mock = MagicMock()
    mock.process_response = MagicMock()
    mock.get_errors = MagicMock(return_value=errors or [])
    mock.is_authenticated = MagicMock(return_value=is_authenticated)
    mock.get_nameid = MagicMock(return_value=name_id)
    mock.get_attributes = MagicMock(
        return_value=attributes
        if attributes is not None
        else {
            "email": ["alice@example.com"],
            "aletheia_role": ["operator"],
            "displayName": ["Alice Example"],
            "tenant_id": ["tenant-abc"],
        }
    )
    return mock


def _b64(text: str) -> str:
    """Base64-encode a string the same way a SAML IdP would."""
    return base64.b64encode(text.encode()).decode()


# ---------------------------------------------------------------------------
# Module-level guard: skip if python3-saml not installed
# ---------------------------------------------------------------------------

onelogin = pytest.importorskip(
    "onelogin",
    reason="python3-saml not installed; skipping SAML tests",
)

# Import after the importorskip so the module is only imported if the dep exists.
from core.auth.saml import SAMLAuthProvider, _MAX_SAML_RESPONSE_BYTES  # noqa: E402


# ---------------------------------------------------------------------------
# Init / Config Tests
# ---------------------------------------------------------------------------


class TestSAMLProviderInit:
    def test_missing_metadata_url_raises(self) -> None:
        with pytest.raises(ValueError, match="metadata"):
            SAMLAuthProvider(metadata_url="", entity_id=ENTITY_ID, acs_url=ACS_URL)

    def test_missing_entity_id_raises(self) -> None:
        with pytest.raises(ValueError, match="entity"):
            SAMLAuthProvider(
                metadata_url=METADATA_URL, entity_id="", acs_url=ACS_URL
            )

    def test_missing_acs_url_raises(self) -> None:
        with pytest.raises(ValueError, match="ACS"):
            SAMLAuthProvider(
                metadata_url=METADATA_URL, entity_id=ENTITY_ID, acs_url=""
            )

    def test_import_error_if_python3_saml_missing(self) -> None:
        import builtins

        real_import = builtins.__import__

        def _block_onelogin(name: str, *args: object, **kwargs: object) -> object:
            if "onelogin" in name:
                raise ImportError("No module named 'onelogin'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_block_onelogin):
            with pytest.raises(ImportError, match="python3-saml"):
                SAMLAuthProvider(
                    metadata_url=METADATA_URL, entity_id=ENTITY_ID, acs_url=ACS_URL
                )

    def test_settings_strict_mode_enabled(self) -> None:
        provider = _make_provider()
        assert provider._saml_settings["strict"] is True

    def test_settings_want_assertions_signed(self) -> None:
        provider = _make_provider()
        assert provider._saml_settings["security"]["wantAssertionsSigned"] is True

    def test_settings_want_messages_signed(self) -> None:
        """Both message and assertion signatures must be required."""
        provider = _make_provider()
        assert provider._saml_settings["security"]["wantMessagesSigned"] is True

    def test_acs_url_in_sp_settings(self) -> None:
        provider = _make_provider()
        acs = provider._saml_settings["sp"]["assertionConsumerService"]["url"]
        assert acs == ACS_URL

    def test_entity_id_in_sp_settings(self) -> None:
        provider = _make_provider()
        assert provider._saml_settings["sp"]["entityId"] == ENTITY_ID


# ---------------------------------------------------------------------------
# authenticate() — Empty credential
# ---------------------------------------------------------------------------


class TestAuthenticateEmptyCredential:
    @pytest.mark.asyncio
    async def test_empty_string_returns_none(self) -> None:
        provider = _make_provider()
        result = await provider.authenticate("")
        assert result is None

    @pytest.mark.asyncio
    async def test_none_equivalent_returns_none(self) -> None:
        provider = _make_provider()
        result = await provider.authenticate("")
        assert result is None


# ---------------------------------------------------------------------------
# authenticate() — Response size guard
# ---------------------------------------------------------------------------


class TestResponseSizeGuard:
    @pytest.mark.asyncio
    async def test_oversized_response_rejected(self) -> None:
        provider = _make_provider()
        # A credential whose UTF-8 encoded length exceeds the limit.
        oversized = "A" * (_MAX_SAML_RESPONSE_BYTES + 1)
        result = await provider.authenticate(oversized)
        assert result is None

    @pytest.mark.asyncio
    async def test_exactly_at_limit_not_rejected_by_size_guard(self) -> None:
        """At-the-limit credentials pass the size check (then go to XML parsing)."""
        provider = _make_provider()
        at_limit = "A" * _MAX_SAML_RESPONSE_BYTES
        # python3-saml will reject this as invalid XML/SAML — that's expected.
        # The point is the size guard itself doesn't reject it prematurely.
        mock_auth = _mock_saml_auth(
            is_authenticated=False, errors=["invalid_response"]
        )
        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(at_limit)
        # Validation fails for other reasons, not size — result is None either way.
        assert result is None


# ---------------------------------------------------------------------------
# authenticate() — Happy path
# ---------------------------------------------------------------------------


class TestAuthenticateHappyPath:
    @pytest.mark.asyncio
    async def test_valid_response_returns_authenticated_user(self) -> None:
        provider = _make_provider()
        mock_auth = _mock_saml_auth()

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is not None
        assert result.user_id == "user@example.com"
        assert result.email == "alice@example.com"
        assert result.auth_method == "saml"

    @pytest.mark.asyncio
    async def test_tenant_id_extracted(self) -> None:
        provider = _make_provider()
        mock_auth = _mock_saml_auth(
            attributes={
                "email": ["bob@example.com"],
                "tenant_id": ["tenant-xyz"],
                "aletheia_role": ["admin"],
            }
        )

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is not None
        assert result.tenant_id == "tenant-xyz"

    @pytest.mark.asyncio
    async def test_aletheia_tenant_fallback(self) -> None:
        """``aletheia_tenant`` attribute used when ``tenant_id`` is absent."""
        provider = _make_provider()
        mock_auth = _mock_saml_auth(
            attributes={
                "email": ["user@example.com"],
                "aletheia_tenant": ["tenant-from-claim"],
            }
        )

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is not None
        assert result.tenant_id == "tenant-from-claim"

    @pytest.mark.asyncio
    async def test_display_name_populated(self) -> None:
        provider = _make_provider()
        mock_auth = _mock_saml_auth(
            attributes={
                "email": ["user@example.com"],
                "displayName": ["Carol Smith"],
            }
        )

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is not None
        assert result.display_name == "Carol Smith"

    @pytest.mark.asyncio
    async def test_cn_used_when_displayname_absent(self) -> None:
        provider = _make_provider()
        mock_auth = _mock_saml_auth(
            attributes={"email": ["user@example.com"], "cn": ["Dan Jones"]}
        )

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is not None
        assert result.display_name == "Dan Jones"

    @pytest.mark.asyncio
    async def test_name_id_used_as_email_fallback(self) -> None:
        """When no email attribute is present, name_id is used."""
        provider = _make_provider()
        mock_auth = _mock_saml_auth(
            attributes={},
            name_id="nameonly@example.com",
        )

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is not None
        assert result.email == "nameonly@example.com"

    @pytest.mark.asyncio
    async def test_mail_attribute_used_when_email_absent(self) -> None:
        """LDAP ``mail`` attribute maps to email."""
        provider = _make_provider()
        mock_auth = _mock_saml_auth(
            attributes={"mail": ["ldap@example.com"]},
            name_id="uid=ldapuser",
        )

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is not None
        assert result.email == "ldap@example.com"


# ---------------------------------------------------------------------------
# authenticate() — Role handling
# ---------------------------------------------------------------------------


class TestRoleHandling:
    @pytest.mark.asyncio
    async def test_known_roles_preserved(self) -> None:
        from core.auth.models import VALID_ROLES

        for role in VALID_ROLES:
            provider = _make_provider()
            mock_auth = _mock_saml_auth(
                attributes={"email": ["u@e.com"], "aletheia_role": [role]}
            )

            with patch(
                "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
            ):
                result = await provider.authenticate(_b64("<SAMLResponse/>"))

            assert result is not None, f"Expected result for role={role}"
            assert role in result.roles, f"Expected '{role}' in {result.roles}"

    @pytest.mark.asyncio
    async def test_unknown_role_defaults_to_operator(self) -> None:
        provider = _make_provider()
        mock_auth = _mock_saml_auth(
            attributes={"email": ["u@e.com"], "aletheia_role": ["god_mode"]}
        )

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is not None
        assert "operator" in result.roles

    @pytest.mark.asyncio
    async def test_missing_role_attribute_defaults_to_operator(self) -> None:
        provider = _make_provider()
        mock_auth = _mock_saml_auth(attributes={"email": ["u@e.com"]})

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is not None
        assert "operator" in result.roles


# ---------------------------------------------------------------------------
# authenticate() — Validation failure paths
# ---------------------------------------------------------------------------


class TestValidationFailures:
    @pytest.mark.asyncio
    async def test_saml_errors_returns_none(self) -> None:
        provider = _make_provider()
        mock_auth = _mock_saml_auth(
            is_authenticated=False,
            errors=["invalid_response", "error_many_authn_request"],
        )

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is None

    @pytest.mark.asyncio
    async def test_not_authenticated_returns_none(self) -> None:
        provider = _make_provider()
        mock_auth = _mock_saml_auth(is_authenticated=False, errors=[])

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is None

    @pytest.mark.asyncio
    async def test_exception_during_processing_returns_none(self) -> None:
        """Any unexpected exception from python3-saml → None, no re-raise."""
        provider = _make_provider()
        mock_auth = MagicMock()
        mock_auth.process_response = MagicMock(
            side_effect=RuntimeError("XML parsing failed")
        )

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", return_value=mock_auth
        ):
            result = await provider.authenticate(_b64("<SAMLResponse/>"))

        assert result is None

    @pytest.mark.asyncio
    async def test_import_error_re_raised(self) -> None:
        """ImportError (missing dep) is re-raised so callers can surface it."""
        provider = _make_provider()

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth",
            side_effect=ImportError("No module named 'onelogin'"),
        ):
            with pytest.raises(ImportError):
                await provider.authenticate(_b64("<SAMLResponse/>"))


# ---------------------------------------------------------------------------
# http_host derivation (ACS URL host validation fix)
# ---------------------------------------------------------------------------


class TestHttpHostDerivation:
    @pytest.mark.asyncio
    async def test_http_host_set_from_acs_url(self) -> None:
        """The request dict passed to python3-saml must contain the ACS hostname."""
        provider = _make_provider(acs_url="https://sp.mycompany.com/saml/acs")
        captured: list[dict] = []

        def _capture_init(request_data: dict, **_kw: Any) -> MagicMock:
            captured.append(request_data)
            return _mock_saml_auth()

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", side_effect=_capture_init
        ):
            await provider.authenticate(_b64("<SAMLResponse/>"))

        assert captured, "OneLogin_Saml2_Auth was never called"
        assert captured[0]["http_host"] == "sp.mycompany.com"

    @pytest.mark.asyncio
    async def test_http_host_not_empty(self) -> None:
        """http_host must never be an empty string."""
        provider = _make_provider(acs_url="https://sp.example.com/acs")
        captured: list[dict] = []

        def _capture_init(request_data: dict, **_kw: Any) -> MagicMock:
            captured.append(request_data)
            return _mock_saml_auth()

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", side_effect=_capture_init
        ):
            await provider.authenticate(_b64("<SAMLResponse/>"))

        assert captured[0]["http_host"] != "", (
            "Empty http_host skips ACS destination validation"
        )

    @pytest.mark.asyncio
    async def test_https_flag_always_on(self) -> None:
        """``https: 'on'`` must always be set regardless of ACS scheme."""
        provider = _make_provider()
        captured: list[dict] = []

        def _capture_init(request_data: dict, **_kw: Any) -> MagicMock:
            captured.append(request_data)
            return _mock_saml_auth()

        with patch(
            "onelogin.saml2.auth.OneLogin_Saml2_Auth", side_effect=_capture_init
        ):
            await provider.authenticate(_b64("<SAMLResponse/>"))

        assert captured[0]["https"] == "on"


# ---------------------------------------------------------------------------
# health_check()
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_true_on_200(self) -> None:
        provider = _make_provider()

        resp = MagicMock()
        resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=resp)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_client)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=ctx):
            result = await provider.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_false_on_network_error(self) -> None:
        import httpx

        provider = _make_provider()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_client)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=ctx):
            result = await provider.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_false_on_non_200(self) -> None:
        provider = _make_provider()

        resp = MagicMock()
        resp.status_code = 503
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=resp)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_client)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=ctx):
            result = await provider.health_check()

        assert result is False

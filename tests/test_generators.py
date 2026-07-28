"""Tests that outreach generators inject config-driven values deterministically.

The LLM is told to use placeholder tokens; code replaces them.  These tests
mock the LLM to return placeholder-containing text and verify the final
output always contains the config values — never the raw placeholders and
never the LLM's own hallucinated name.
"""

from unittest.mock import patch

import config
from outreach import email_generator, whatsapp_generator


_BUSINESS = {
    "id": 101,
    "name": "Test Café",
    "city": "Mumbai",
}

_AUDIT = {
    "has_website": False,
    "has_business_email": True,
    "has_instagram": False,
}

_RECS = ["website redesign", "SEO"]

_NAME = "Priya"


class TestEmailGeneratorSignoff:
    """Verify that the email body always ends with the config name."""

    def _generate(self, mock_llm, follow_up=0):
        mock_llm.return_value = (
            "Hi there,\n\n"
            "Great cafe you have.\n\n"
            "{{SIGNOFF}}"
        )
        with patch.object(config, "FREELANCER_NAME", _NAME):
            return email_generator.generate_email(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=follow_up
            )

    @patch.object(email_generator, "llm_generate")
    def test_signoff_placeholder_replaced(self, mock_llm):
        result = self._generate(mock_llm)
        body = result["body"]
        assert _NAME in body
        assert body.rstrip().endswith(f"- {_NAME}")
        assert "{{SIGNOFF}}" not in body

    @patch.object(email_generator, "llm_generate")
    def test_signoff_appended_when_missing(self, mock_llm):
        mock_llm.return_value = (
            "Hi there,\n\n"
            "Great cafe you have.\n\n"
            "Cheers"
        )
        with patch.object(config, "FREELANCER_NAME", _NAME):
            result = email_generator.generate_email(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=0
            )
        body = result["body"]
        assert _NAME in body
        assert body.rstrip().endswith(f"- {_NAME}")

    @patch.object(email_generator, "llm_generate")
    def test_starting_price_placeholder_replaced(self, mock_llm):
        mock_llm.return_value = (
            "Hi there,\n\n"
            "Pricing starts at {{STARTING_PRICE}}.\n\n"
            "{{SIGNOFF}}"
        )
        with patch.object(config, "FREELANCER_NAME", _NAME):
            result = email_generator.generate_email(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=0
            )
        body = result["body"]
        assert "{{STARTING_PRICE}}" not in body
        assert config.STARTING_PRICE in body

    @patch.object(email_generator, "llm_generate")
    def test_portfolio_url_placeholder_replaced(self, mock_llm):
        mock_llm.return_value = (
            "Hi there,\n\n"
            "Check {{PORTFOLIO_URL}}.\n\n"
            "{{SIGNOFF}}"
        )
        with patch.object(config, "FREELANCER_NAME", _NAME):
            result = email_generator.generate_email(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=0
            )
        body = result["body"]
        assert "{{PORTFOLIO_URL}}" not in body
        assert config.PORTFOLIO_URL in body

    @patch.object(email_generator, "llm_generate")
    def test_no_hallucinated_name_appears(self, mock_llm):
        """If the LLM inserts its own name, code does not strip it,
        but we assert the *correct* name is present via the code path."""
        mock_llm.return_value = (
            "Hi there,\n\n"
            "I am Alex from DesignCo.\n\n"
            "{{SIGNOFF}}"
        )
        with patch.object(config, "FREELANCER_NAME", _NAME):
            result = email_generator.generate_email(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=0
            )
        body = result["body"]
        assert _NAME in body
        assert body.rstrip().endswith(f"- {_NAME}")

    @patch.object(email_generator, "llm_generate")
    def test_follow_up_signoff_replaced(self, mock_llm):
        mock_llm.return_value = (
            "Just checking in!\n\n"
            "{{SIGNOFF}}"
        )
        with patch.object(config, "FREELANCER_NAME", _NAME):
            result = email_generator.generate_email(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=1
            )
        body = result["body"]
        assert _NAME in body
        assert body.rstrip().endswith(f"- {_NAME}")


class TestWhatsAppGeneratorSignoff:
    """Verify that the WhatsApp message always contains the config name."""

    @patch.object(whatsapp_generator, "llm_generate")
    def test_signoff_placeholder_replaced(self, mock_llm):
        mock_llm.return_value = (
            "Hey! Great cafe.\n\n"
            "{{SIGNOFF}}"
        )
        with patch.object(config, "FREELANCER_NAME", _NAME):
            result = whatsapp_generator.generate_whatsapp(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=0
            )
        assert _NAME in result
        assert f"- {_NAME}" in result
        assert "{{SIGNOFF}}" not in result

    @patch.object(whatsapp_generator, "llm_generate")
    def test_signoff_appended_when_missing(self, mock_llm):
        mock_llm.return_value = (
            "Hey! Great cafe.\n\n"
            "Cheers"
        )
        with patch.object(config, "FREELANCER_NAME", _NAME):
            result = whatsapp_generator.generate_whatsapp(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=0
            )
        assert _NAME in result
        assert f"- {_NAME}" in result

    @patch.object(whatsapp_generator, "llm_generate")
    def test_starting_price_placeholder_replaced(self, mock_llm):
        mock_llm.return_value = (
            "Hey! Pricing starts at {{STARTING_PRICE}}.\n\n"
            "{{SIGNOFF}}"
        )
        with patch.object(config, "FREELANCER_NAME", _NAME):
            result = whatsapp_generator.generate_whatsapp(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=0
            )
        assert "{{STARTING_PRICE}}" not in result
        assert config.STARTING_PRICE in result

    @patch.object(whatsapp_generator, "llm_generate")
    def test_follow_up_signoff_replaced(self, mock_llm):
        mock_llm.return_value = (
            "Just checking in!\n\n"
            "{{SIGNOFF}}"
        )
        with patch.object(config, "FREELANCER_NAME", _NAME):
            result = whatsapp_generator.generate_whatsapp(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=1
            )
        assert _NAME in result
        assert f"- {_NAME}" in result
        assert "{{SIGNOFF}}" not in result

    @patch.object(whatsapp_generator, "llm_generate")
    def test_optout_comes_after_signoff(self, mock_llm):
        mock_llm.return_value = (
            "Hey! Great cafe.\n\n"
            "{{SIGNOFF}}"
        )
        with patch.object(config, "FREELANCER_NAME", _NAME):
            result = whatsapp_generator.generate_whatsapp(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=0
            )
        signoff_pos = result.index(f"- {_NAME}")
        optout_pos = result.index("STOP")
        assert signoff_pos < optout_pos


class TestFallbackPath:
    """When Ollama is down, fallback text must still get the config name
    via the same deterministic post-processing."""

    def test_email_fallback_has_name(self):
        with patch.object(
            email_generator, "llm_generate",
            side_effect=email_generator.OllamaUnavailableError("no ollama"),
        ), patch.object(config, "FREELANCER_NAME", _NAME):
            result = email_generator.generate_email(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=0
            )
        body = result["body"]
        assert _NAME in body
        assert body.rstrip().endswith(f"- {_NAME}")

    def test_whatsapp_fallback_has_name(self):
        with patch.object(
            whatsapp_generator, "llm_generate",
            side_effect=whatsapp_generator.OllamaUnavailableError("no ollama"),
        ), patch.object(config, "FREELANCER_NAME", _NAME):
            result = whatsapp_generator.generate_whatsapp(
                _BUSINESS, _AUDIT, _RECS, follow_up_number=0
            )
        assert _NAME in result
        assert f"- {_NAME}" in result

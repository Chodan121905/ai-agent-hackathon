"""Deterministic impostor detection — no network, runs anywhere (PLAN §7.3, req 5)."""
from __future__ import annotations

from app.integrations import email_forensics


def test_display_name_vs_real_address_mismatch():
    sa = email_forensics.analyze_headers(
        {"From": '"DBS Bank Security" <alerts@dbs-verify.ru>', "Subject": "Verify now"},
        body="Your account is suspended.",
    )
    assert sa["claimed_brand"] == "dbs"
    assert sa["display_name_mismatch"] is True
    assert sa["from_address"] == "alerts@dbs-verify.ru"
    assert sa["reasons"]


def test_freemail_as_company():
    sa = email_forensics.analyze_headers(
        {"From": '"IRAS Tax" <iras.refund@gmail.com>'}, body="Tax refund pending."
    )
    assert sa["freemail_as_company"] is True


def test_legit_sender_is_clean():
    sa = email_forensics.analyze_headers(
        {"From": '"DBS" <noreply@dbs.com.sg>'}, body="Statement ready."
    )
    assert sa["display_name_mismatch"] is False
    assert sa["lookalike_domain"] is False


def test_auth_failure_flagged():
    sa = email_forensics.analyze_headers(
        {
            "From": "support@paypal.com",
            "Authentication-Results": "mx.google.com; spf=fail dkim=none dmarc=fail",
        },
        body="hi",
    )
    assert sa["auth_results"] is not None
    assert "fail" in sa["auth_results"]


def test_replyto_mismatch():
    sa = email_forensics.analyze_headers(
        {"From": "service@ocbc.com", "Reply-To": "random@mailinator.com"}, body="hi"
    )
    assert sa["replyto_mismatch"] is True

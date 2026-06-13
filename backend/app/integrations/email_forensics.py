"""Deterministic impostor / spoofed-sender detection (PLAN §7.3, requirement 5).

Computes hard signals from raw email headers BEFORE the LLM sees the content, so a
phishing email is caught even when the wording looks innocent. No network calls.
"""
from __future__ import annotations

import re
from email.utils import getaddresses, parseaddr

import tldextract

# Known brands → their canonical registrable domains (small demo list; extend freely).
BRAND_DOMAINS: dict[str, set[str]] = {
    "dbs": {"dbs.com", "dbs.com.sg"},
    "posb": {"posb.com.sg"},
    "ocbc": {"ocbc.com"},
    "uob": {"uob.com.sg", "uobgroup.com"},
    "citibank": {"citi.com", "citibank.com"},
    "hsbc": {"hsbc.com", "hsbc.com.sg"},
    "maybank": {"maybank.com", "maybank2u.com.sg"},
    "paypal": {"paypal.com"},
    "apple": {"apple.com"},
    "google": {"google.com"},
    "microsoft": {"microsoft.com", "outlook.com"},
    "amazon": {"amazon.com", "amazon.sg"},
    "netflix": {"netflix.com"},
    "singpost": {"singpost.com"},
    "iras": {"iras.gov.sg"},
    "cpf": {"cpf.gov.sg"},
    "mom": {"mom.gov.sg"},
    "shopee": {"shopee.sg", "shopee.com"},
    "lazada": {"lazada.sg", "lazada.com"},
    "dhl": {"dhl.com"},
    "fedex": {"fedex.com"},
}

FREEMAIL = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com",
    "yahoo.com", "yahoo.com.sg", "ymail.com", "qq.com", "163.com", "126.com",
    "proton.me", "protonmail.com", "icloud.com", "aol.com", "mail.com",
}

_BRAND_ALIASES = {
    "dbs bank": "dbs", "dbs security": "dbs", "iras tax": "iras",
    "apple support": "apple", "microsoft account": "microsoft",
}


def _registrable(addr: str) -> str:
    """Return the registrable domain (e.g. 'dbs.com.sg') for an email address or domain."""
    domain = addr.split("@")[-1].strip().lower().strip(">").strip()
    ext = tldextract.extract(domain)
    return ".".join(p for p in [ext.domain, ext.suffix] if p)


def _detect_brand(display_name: str, body: str) -> str | None:
    blob = f"{display_name} {body[:500]}".lower()
    for alias, brand in _BRAND_ALIASES.items():
        if alias in blob:
            return brand
    for brand in BRAND_DOMAINS:
        if re.search(rf"\b{re.escape(brand)}\b", blob):
            return brand
    return None


def _is_punycode_or_homoglyph(domain: str) -> bool:
    if "xn--" in domain:
        return True
    # any non-ascii char in a domain that claims to be a latin brand → homoglyph attempt
    return any(ord(c) > 127 for c in domain)


def _is_lookalike(domain: str, brand: str) -> bool:
    """Brand token appears in the domain but the domain is NOT the brand's real one."""
    legit = BRAND_DOMAINS.get(brand, set())
    reg = _registrable(domain)
    if reg in legit:
        return False
    # brand string embedded with extra words / hyphens / wrong tld, e.g. dbs-verify.ru
    return brand in domain.replace(".", "").replace("-", "") or brand in domain


def analyze_headers(headers: dict, body: str = "") -> dict:
    """headers: dict of raw header name -> value. Returns a SenderAnalysis-shaped dict."""
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    reasons: list[str] = []

    raw_from = headers.get("from", "")
    display_name, from_addr = parseaddr(raw_from)
    from_addr = from_addr.lower()
    from_reg = _registrable(from_addr) if from_addr else ""

    claimed_brand = _detect_brand(display_name, body)

    display_name_mismatch = False
    lookalike_domain = False
    freemail_as_company = False

    if claimed_brand and from_reg:
        legit = BRAND_DOMAINS.get(claimed_brand, set())
        if from_reg not in legit:
            display_name_mismatch = True
            reasons.append(
                f'Sender shows "{display_name or claimed_brand}" but the real address '
                f"is {from_addr or 'unknown'} — not {claimed_brand}'s domain."
            )
        if _is_lookalike(from_reg, claimed_brand) and from_reg not in legit:
            lookalike_domain = True
            reasons.append(f"{from_reg} is a look-alike of {claimed_brand}'s real domain.")
        if from_reg in FREEMAIL:
            freemail_as_company = True
            reasons.append(
                f"Claims to be {claimed_brand} but uses a free email account ({from_reg})."
            )

    if from_reg and _is_punycode_or_homoglyph(from_addr):
        lookalike_domain = True
        reasons.append(f"Sender domain uses look-alike/punycode characters ({from_addr}).")

    # Reply-To / Return-Path mismatch
    replyto_mismatch = False
    for hdr in ("reply-to", "return-path"):
        val = headers.get(hdr, "")
        if val:
            _, raddr = parseaddr(val)
            rreg = _registrable(raddr) if raddr else ""
            if rreg and from_reg and rreg != from_reg:
                replyto_mismatch = True
                reasons.append(f"{hdr.title()} ({rreg}) differs from the From domain ({from_reg}).")
                break

    # SPF / DKIM / DMARC
    auth = headers.get("authentication-results", "") or headers.get("arc-authentication-results", "")
    auth_summary = None
    if auth:
        found = {}
        for mech in ("spf", "dkim", "dmarc"):
            m = re.search(rf"{mech}=(\w+)", auth, re.IGNORECASE)
            if m:
                found[mech] = m.group(1).lower()
        if found:
            auth_summary = " ".join(f"{k}={v}" for k, v in found.items())
            if any(v in ("fail", "softfail", "none") for v in found.values()):
                reasons.append(f"Email authentication issues: {auth_summary}.")

    return {
        "from_display_name": display_name or None,
        "from_address": from_addr or None,
        "claimed_brand": claimed_brand,
        "display_name_mismatch": display_name_mismatch,
        "lookalike_domain": lookalike_domain,
        "freemail_as_company": freemail_as_company,
        "replyto_mismatch": replyto_mismatch,
        "auth_results": auth_summary,
        "reasons": reasons,
    }


def collect_addresses(headers: dict) -> list[str]:
    """All addresses across From/To/Cc, for logging/debug."""
    pairs = getaddresses([v for v in (headers or {}).values()])
    return [a for _, a in pairs if a]

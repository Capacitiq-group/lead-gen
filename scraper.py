"""
Core scraping/crawling logic.

Two jobs:
1. find_candidate_urls(query)  -> search DuckDuckGo's HTML endpoint (no API
   key needed) and return a list of candidate business website URLs.
2. analyze_website(url)        -> fetch that site and pull out everything we
   care about: email, phone, whatsapp, socials, contact person, whether it
   has a contact form, and whether it has a live-chat widget.

Both are deliberately conservative and slow (random delays, small retry
budget) because we're relying on public HTML pages rather than a paid API,
and being a polite, low-volume caller is what keeps this working at all.
"""

import random
import re
import time
import urllib.parse as urlparse
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": config.USER_AGENT})

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9.\-_%+]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)
# South African phone formats: 0xx xxx xxxx or +27 xx xxx xxxx
PHONE_RE = re.compile(
    r"(?:\+27[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{4})"
    r"|(?:0\d{2}[\s\-]?\d{3}[\s\-]?\d{4})"
)
WHATSAPP_RE = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\d+)")

SOCIAL_DOMAINS = {
    "linkedin": "linkedin.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "twitter": "twitter.com",
    "x": "x.com",
    "tiktok": "tiktok.com",
    "youtube": "youtube.com",
}

# Generic junk domains that show up in search results but aren't businesses
BLOCKED_DOMAINS = {
    "facebook.com", "instagram.com", "linkedin.com", "youtube.com",
    "twitter.com", "x.com", "wikipedia.org", "yelp.com", "yellowpages.co.za",
    "google.com", "maps.google.com", "duckduckgo.com", "tiktok.com",
    "pinterest.com", "indeed.com", "gumtree.co.za",
}


@dataclass
class SiteResult:
    business_name: str
    category: str
    website: str
    reachable: bool = False
    has_chat_widget: Optional[bool] = None
    has_contact_form: Optional[bool] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    linkedin: Optional[str] = None
    other_socials: List[str] = field(default_factory=list)
    contact_person: Optional[str] = None
    source_query: str = ""
    notes: str = ""

    def passes_filters(self) -> bool:
        """Hard requirements from the brief: reachable website, no chat
        widget, and an email address. Everything else is a bonus field."""
        return bool(self.reachable and not self.has_chat_widget and self.email)


def _polite_delay():
    time.sleep(random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS))


def _get(url: str, **kwargs) -> Optional[requests.Response]:
    for attempt in range(config.MAX_RETRIES + 1):
        try:
            resp = SESSION.get(url, timeout=config.REQUEST_TIMEOUT, **kwargs)
            if resp.status_code == 200:
                return resp
            # 429/403 usually means we're being rate-limited — back off harder
            if resp.status_code in (429, 403):
                time.sleep(config.MAX_DELAY_SECONDS * (attempt + 2))
                continue
            return None
        except requests.RequestException:
            time.sleep(config.MIN_DELAY_SECONDS)
            continue
    return None


def find_candidate_urls(query: str, max_results: int = None) -> List[str]:
    """Search DuckDuckGo's HTML endpoint (no API key required) and return
    candidate business homepage URLs, deduplicated and with junk domains
    filtered out."""
    max_results = max_results or config.SEARCH_RESULTS_PER_QUERY
    _polite_delay()
    resp = _get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp is None:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    urls = []
    for a in soup.select("a.result__a"):
        href = a.get("href", "")
        real_url = _unwrap_duckduckgo_redirect(href)
        if not real_url:
            continue
        domain = urlparse.urlparse(real_url).netloc.lower().replace("www.", "")
        if any(blocked in domain for blocked in BLOCKED_DOMAINS):
            continue
        base = f"{urlparse.urlparse(real_url).scheme}://{urlparse.urlparse(real_url).netloc}"
        if base not in urls:
            urls.append(base)
        if len(urls) >= max_results:
            break
    return urls


def _unwrap_duckduckgo_redirect(href: str) -> Optional[str]:
    """DuckDuckGo's HTML results wrap links as /l/?uddg=<encoded real url>."""
    if not href:
        return None
    if href.startswith("//duckduckgo.com/l/"):
        href = "https:" + href
    parsed = urlparse.urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        qs = urlparse.parse_qs(parsed.query)
        real = qs.get("uddg", [None])[0]
        return urlparse.unquote(real) if real else None
    if href.startswith("http"):
        return href
    return None


def analyze_website(category: str, url: str, source_query: str) -> SiteResult:
    """Fetch a candidate site's homepage (and contact page if findable) and
    extract everything the filters/output need. Business name is derived
    from the page's <title> tag since search results don't reliably give
    us a clean company name."""
    result = SiteResult(
        business_name="", category=category, website=url,
        source_query=source_query,
    )

    _polite_delay()
    resp = _get(url)
    if resp is None:
        result.reachable = False
        result.notes = "site unreachable or blocked crawler"
        return result

    result.reachable = True
    html = resp.text
    result.has_chat_widget = _detect_chat_widget(html)

    soup = BeautifulSoup(html, "html.parser")
    result.has_contact_form = bool(soup.find("form"))
    result.business_name = _derive_business_name(soup, url)

    _extract_contacts(html, soup, url, result)

    # If no email found on homepage, try a likely contact/about page
    if not result.email:
        contact_url = _find_contact_page(soup, url)
        if contact_url:
            _polite_delay()
            resp2 = _get(contact_url)
            if resp2 is not None:
                soup2 = BeautifulSoup(resp2.text, "html.parser")
                if result.has_chat_widget is False:
                    result.has_chat_widget = _detect_chat_widget(resp2.text)
                if not result.has_contact_form:
                    result.has_contact_form = bool(soup2.find("form"))
                _extract_contacts(resp2.text, soup2, contact_url, result)

    return result


def _detect_chat_widget(html: str) -> bool:
    lowered = html.lower()
    return any(sig.lower() in lowered for sig in config.CHAT_WIDGET_SIGNATURES)


def _extract_contacts(html: str, soup: BeautifulSoup, page_url: str, result: SiteResult):
    # Email — prefer mailto: links, fall back to regex over visible text
    if not result.email:
        mailto = soup.select_one('a[href^="mailto:"]')
        if mailto:
            addr = mailto.get("href", "").replace("mailto:", "").split("?")[0].strip()
            if EMAIL_RE.match(addr):
                result.email = addr
    if not result.email:
        match = EMAIL_RE.search(html)
        if match:
            result.email = match.group(0)

    # Phone
    if not result.phone:
        match = PHONE_RE.search(html)
        if match:
            result.phone = match.group(0).strip()

    # WhatsApp
    if not result.whatsapp:
        match = WHATSAPP_RE.search(html)
        if match:
            result.whatsapp = match.group(1)

    # Socials
    for a in soup.find_all("a", href=True):
        href = a["href"]
        domain = urlparse.urlparse(href).netloc.lower()
        if "linkedin.com" in domain and not result.linkedin:
            result.linkedin = href
        for name, dom in SOCIAL_DOMAINS.items():
            if dom in domain and dom != "linkedin.com":
                full = href if href.startswith("http") else urljoin(page_url, href)
                if full not in result.other_socials:
                    result.other_socials.append(full)

    # Very light "contact person" heuristic — look for common founder/owner
    # phrasing near a name-shaped token. This is intentionally conservative;
    # most of the time this field will stay empty, which is fine.
    if not result.contact_person:
        person = _guess_contact_person(soup)
        if person:
            result.contact_person = person


def _guess_contact_person(soup: BeautifulSoup) -> Optional[str]:
    keywords = ["founder", "owner", "director", "principal", "proprietor", "managing director"]
    text_blocks = soup.find_all(["p", "li", "span", "div", "h3", "h4"])
    for block in text_blocks:
        text = block.get_text(" ", strip=True)
        if not text or len(text) > 200:
            continue
        lowered = text.lower()
        if any(k in lowered for k in keywords):
            # crude name guess: look for two capitalised words near the keyword
            name_match = re.search(r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})", text)
            if name_match:
                return name_match.group(1)
    return None


def _derive_business_name(soup: BeautifulSoup, url: str) -> str:
    title_tag = soup.find("title")
    if title_tag and title_tag.get_text(strip=True):
        title = title_tag.get_text(strip=True)
        # Strip common suffixes like " | Home" or " - Official Site"
        title = re.split(r"[|\-–—]", title)[0].strip()
        if title:
            return title
    og_site = soup.find("meta", attrs={"property": "og:site_name"})
    if og_site and og_site.get("content"):
        return og_site["content"].strip()
    # Fallback: domain name, title-cased
    domain = urlparse.urlparse(url).netloc.replace("www.", "").split(".")[0]
    return domain.replace("-", " ").title()


def _find_contact_page(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").lower()
        href = a["href"].lower()
        if "contact" in text or "contact" in href:
            return urljoin(base_url, a["href"])
    return None

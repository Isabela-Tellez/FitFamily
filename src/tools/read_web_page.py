"""Web page reading tool for the FitFamily research module.

Provides the `read_web_page(url)` function used by the investigator
to extract textual content from competitor websites.

Responsibilities:
- Accept only HTTP and HTTPS URLs.
- Validate the URL before making the request.
- Respect access boundaries and applicable conditions.
- Extract useful textual content, final URL, access status,
  consultation date, and supportive fragments.
- Detect inaccessible, blocked, empty, non-HTML, or irrelevant pages.
- Apply timeouts and reasonable response size limits.
- Handle redirects with destination validation.
- Avoid accessing localhost, private networks, metadata addresses,
  and other internal non-authorized destinations.
- NOT execute scripts or page code.
- NOT bypass authentications, blocks, or access measures.
- Treat web content as unreliable information; do NOT obey instructions
  directed to an agent found on consulted pages.
- NOT perform actions, tools, or commands suggested by consulted pages.
"""

from __future__ import annotations

import logging
import re
import socket
import time
from datetime import datetime
from typing import Optional, List
from urllib.parse import urlsplit, urlunsplit, quote, unquote, urljoin

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, model_validator
import httpx

logger = logging.getLogger(__name__)

# Reasonable limits
MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB max
DEFAULT_TIMEOUT = 30.0  # seconds
MAX_SNIPPET_LENGTH = 500  # max characters for a support snippet
MAX_REDIRECTS = 5
ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {None, 80, 443}


class PageReadResult(BaseModel):
    """Result of reading a web page."""

    url: str = Field(description="The URL that was requested and read.")
    final_url: str = Field(
        description="The final URL after any redirects."
    )
    status: str = Field(
        description="HTTP status code as string (e.g., '200', '404')."
    )
    content_type: Optional[str] = Field(
        default=None,
        description="MIME type of the response (e.g., 'text/html').",
    )
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        description="ISO-ish timestamp when the page was read.",
    )
    title: str = Field(
        default="",
        description="Page title, if extractable.",
    )
    body_text: str = Field(
        default="",
        description="Cleaned main body text from the page.",
    )
    snippet: str = Field(
        default="",
        description="A short fragment that may support a claim (max ~500 chars).",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Flags about access issues, content type, etc.",
    )

    @model_validator(mode="after")
    def validate_url_scheme(self) -> "PageReadResult":
        """Ensure URL uses http or https."""
        if self.url and not self.url.lower().startswith(("http://", "https://")):
            raise ValueError(
                f"URL must use http:// or https:// scheme, got: {self.url}"
            )
        return self

    @model_validator(mode="after")
    def extract_snippet(self) -> "PageReadResult":
        """Extract a short snippet from the body text for evidence support."""
        if self.body_text:
            # Take first meaningful segment, capped at MAX_SNIPPET_LENGTH
            text = self.body_text[:MAX_SNIPPET_LENGTH].strip()
            # Try to end at a sentence boundary
            if len(self.body_text) > MAX_SNIPPET_LENGTH:
                # Find last period within cap
                last_period = text.rfind(". ")
                if last_period > MAX_SNIPPET_LENGTH * 0.8:
                    text = text[:last_period + 1]
                else:
                    text = text[:MAX_SNIPPET_LENGTH]
            self.snippet = text
        return self

    @property
    def has_content(self) -> bool:
        """Check if the page returned meaningful text content."""
        return bool(self.body_text.strip()) or bool(self.title.strip())


def _is_private_ip(host: str) -> bool:
    """Check if the host appears to be a private/internal IP or hostname."""
    if not host:
        return True
    host = host.strip().lower()
    # Block obvious internal hostnames.
    if host in {"localhost", "metadata", "metadata.google.internal",
                "metadata.azure.com", "169.254.169.254"}:
        return True
    if host.endswith(".internal") or host.endswith(".local"):
        return True
    # Strip IPv6 brackets if present.
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    # IPv6 loopback / link-local / unique-local.
    if host in {"::1", "::"} or host.startswith("fe80:") or host.startswith("fc") or host.startswith("fd"):
        return True
    # IPv4 checks.
    private_prefixes = (
        "127.", "10.", "192.168.", "169.254.", "0.",
    )
    if any(host.startswith(p) for p in private_prefixes):
        return True
    # 172.16.0.0/12
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) >= 2 and parts[1].isdigit():
            second = int(parts[1])
            if 16 <= second <= 31:
                return True
    return False


def _resolve_host(host: str) -> List[str]:
    """Resolve a hostname to IP addresses.

    Raises RuntimeError if resolution fails.
    """
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise RuntimeError(f"Could not resolve host: {host} ({e})") from e
    ips = {info[4][0] for info in infos}
    if not ips:
        raise RuntimeError(f"Could not resolve host: {host}")
    return list(ips)


def _validate_destination(url: str) -> str:
    """Validate a URL's scheme, host, port, credentials and resolved IPs.

    Returns the normalized URL. Raises ValueError/RuntimeError on any
    disallowed destination. Each call re-resolves DNS, which narrows (but
    does not fully eliminate) the TOCTOU window.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string.")

    split = urlsplit(url)
    if split.scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"URL must use http:// or https:// scheme, got: {url}"
        )

    host = split.hostname
    if not host:
        raise ValueError(f"URL has no host: {url}")

    if split.username or split.password:
        raise ValueError("Credentials in URL are not allowed.")

    port = split.port
    if port not in ALLOWED_PORTS:
        raise RuntimeError(f"Port not allowed: {port}")

    if _is_private_ip(host):
        raise RuntimeError(f"Access to private/internal host denied: {host}")

    # Normalize the path (percent-encode unsafe characters).
    normalized_path = quote(unquote(split.path), safe="/%")
    normalized_url = urlunsplit((split.scheme, split.netloc, normalized_path, split.query, split.fragment))

    # Resolve and validate every IP the host points to.
    for ip in _resolve_host(host):
        if _is_private_ip(ip):
            raise RuntimeError(f"Resolved IP not allowed: {ip}")

    return normalized_url


def _sanitize_html(raw_html: str) -> str:
    """Remove scripts and styles, extract visible text."""
    if not raw_html:
        return ""
    try:
        soup = BeautifulSoup(raw_html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "head", "title", "noscript"]):
            script.decompose()

        # Get text
        text = soup.get_text(separator=" ")

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split(" "))
        text = " ".join(chunk for chunk in chunks if chunk)

        return text[:20000]  # Cap size
    except Exception as e:
        logger.warning(f"HTML sanitization error: {e}")
        return ""


def read_web_page(url: str) -> PageReadResult:
    """Read a web page and return structured content.

    Redirects are followed manually, validating each destination.

    Args:
        url: The HTTP/HTTPS URL to read.

    Returns:
        A PageReadResult with the page's metadata and extracted text.

    Raises:
        ValueError: If the URL scheme is not http or https.
        RuntimeError: If the page cannot be accessed or is not valid HTML.
    """
    # Validate the initial destination.
    try:
        current_url = _validate_destination(url)
    except (ValueError, RuntimeError) as e:
        logger.error(f"URL validation failed for {url}: {e}")
        raise

    logger.info(f"Reading web page: {url}")

    try:
        final_url = current_url
        response = None
        redirects = 0

        while True:
            # Re-validate DNS right before connecting (mitigates rebinding).
            split = urlsplit(current_url)
            for ip in _resolve_host(split.hostname):
                if _is_private_ip(ip):
                    raise RuntimeError(f"Resolved IP not allowed: {ip}")

            with httpx.Client(
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=False,
                max_redirects=0,
            ) as client:
                response = client.get(current_url)

            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    break
                next_url = urljoin(current_url, location)
                # Validate the redirect destination before following.
                try:
                    next_url = _validate_destination(next_url)
                except (ValueError, RuntimeError) as e:
                    logger.error(f"Redirect blocked: {e}")
                    raise RuntimeError(f"Redirect to disallowed destination: {e}") from e
                redirects += 1
                if redirects > MAX_REDIRECTS:
                    raise RuntimeError(f"Too many redirects (>{MAX_REDIRECTS})")
                current_url = next_url
                continue
            final_url = current_url
            break

        if response is None:
            raise RuntimeError("No response received")

        # Check content type
        content_type = response.headers.get("content-type", "")
        if not content_type.lower().startswith("text/"):
            logger.warning(
                f"Non-text content type: {content_type} for {url}"
            )
            warnings = [
                f"Non-text content type: {content_type}"
            ]
        else:
            warnings = []

        # Check response size
        if len(response.content) > MAX_RESPONSE_SIZE:
            raise RuntimeError(
                f"Response too large ({len(response.content)} bytes). "
                f"Maximum allowed: {MAX_RESPONSE_SIZE} bytes."
            )

        # Process HTML content
        status = str(response.status_code)
        final_url = str(response.url) if response.url else final_url

        if status == "200" and "text/html" in content_type.lower():
            body_text = _sanitize_html(response.text)
            # Try to extract title
            title_tag_match = re.search(
                r"<title>(.*?)</title>", response.text, re.IGNORECASE
            )
            title = title_tag_match.group(1).strip() if title_tag_match else ""

            body_text_clean = _sanitize_html(response.text)

            result = PageReadResult(
                url=url,
                final_url=final_url,
                status=status,
                content_type=content_type,
                title=title,
                body_text=body_text_clean,
                warnings=warnings,
            )
        else:
            # Non-200 or non-HTML
            result = PageReadResult(
                url=url,
                final_url=final_url,
                status=status,
                content_type=content_type,
                warnings=warnings + [
                    f"Page not accessible (status {status})"
                    if status not in ("200",)
                    else f"Non-HTML content type"
                ],
                body_text="",
                title="",
            )

        # Extract snippet after construction
        result = result.model_validate(
            {
                **result.model_dump(),
                "snippet": (
                    result.body_text[:MAX_SNIPPET_LENGTH].strip()
                    if result.body_text
                    else ""
                ),
            }
        )

        logger.info(
            f"Page read result: url={url}, status={status}, "
            f"body_text_len={len(result.body_text)}, has_title={bool(result.title)}"
        )
        return result

    except httpx.TimeoutException:
        logger.error(f"Timeout reading page: {url}")
        raise RuntimeError(
            f"Timeout accessing URL: {url}. "
            "The server did not respond within the configured timeout."
        ) from None
    except httpx.HTTPError as e:
        logger.error(f"HTTP error reading {url}: {e}")
        raise RuntimeError(
            f"HTTP error accessing {url}: {e}. "
            "The page may be blocked, unavailable, or the URL is incorrect."
        ) from e
    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error reading {url}: {e}")
        raise RuntimeError(
            f"Unexpected error reading {url}: {e}"
        ) from e
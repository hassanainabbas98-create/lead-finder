"""Safe website reachability and HTTP status checker with redirect revalidation and size limits."""

import time
import requests
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse
from pydantic import BaseModel

from app.config import settings
from app.services.website.ssrf_guard import validate_url_safe, SSRFSecurityException


class WebsiteCheckResult(BaseModel):
    url: str
    final_url: Optional[str] = None
    http_status: Optional[int] = None
    status_classification: str  # 'Website Found', 'Website Inaccessible', 'Website Check Failed', 'No Website Listed'
    has_https: bool = False
    html_content: Optional[str] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None


class SafeWebsiteChecker:
    """Safe website presence checker with SSRF protection, size limits, and timeouts."""

    def __init__(
        self,
        timeout_seconds: Optional[int] = None,
        max_redirects: Optional[int] = None,
        max_size_bytes: Optional[int] = None,
    ):
        self.timeout = timeout_seconds or settings.HTTP_TIMEOUT_SECONDS
        self.max_redirects = max_redirects or settings.HTTP_MAX_REDIRECTS
        self.max_size = max_size_bytes or settings.MAX_RESPONSE_SIZE_BYTES
        self.user_agent = settings.USER_AGENT

    def check_website(self, raw_url: Optional[str]) -> WebsiteCheckResult:
        """
        Safely check website reachability, follow safe redirects, and return content.
        """
        if not raw_url or not raw_url.strip():
            return WebsiteCheckResult(
                url="",
                status_classification="No Website Listed",
                error_message="No website URL provided in source record.",
            )

        # Normalize scheme if omitted
        url = raw_url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url

        current_url = url
        redirect_count = 0
        start_time = time.time()

        session = requests.Session()
        session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

        while redirect_count <= self.max_redirects:
            # SSRF validation before every hop
            is_safe, reason, _ = validate_url_safe(current_url)
            if not is_safe:
                return WebsiteCheckResult(
                    url=url,
                    final_url=current_url,
                    status_classification="Website Check Failed",
                    error_message=f"SSRF Protection blocked request: {reason}",
                )

            try:
                resp = session.get(
                    current_url,
                    allow_redirects=False,
                    timeout=self.timeout,
                    stream=True,
                )

                # Check for redirects (301, 302, 303, 307, 308)
                if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        break  # Malformed redirect without location
                    current_url = urljoin(current_url, location)
                    redirect_count += 1
                    continue

                # Final response reached
                elapsed_ms = round((time.time() - start_time) * 1000, 2)
                status_code = resp.status_code

                # Status classification
                if 200 <= status_code < 400:
                    status_class = "Website Found"
                elif status_code in (401, 403, 404, 410, 500, 502, 503, 504):
                    status_class = "Website Inaccessible"
                else:
                    status_class = "Website Check Failed"

                # Check Content-Type (prefer HTML)
                content_type = resp.headers.get("Content-Type", "").lower()

                # Stream response content with size enforcement
                chunks = []
                bytes_read = 0
                for chunk in resp.iter_content(chunk_size=8192, decode_unicode=True):
                    if chunk:
                        if isinstance(chunk, str):
                            chunks.append(chunk)
                            bytes_read += len(chunk.encode("utf-8", errors="ignore"))
                        elif isinstance(chunk, bytes):
                            decoded = chunk.decode("utf-8", errors="ignore")
                            chunks.append(decoded)
                            bytes_read += len(chunk)
                        if bytes_read > self.max_size:
                            break  # Hit maximum allowed response limit

                html_text = "".join(chunks)

                return WebsiteCheckResult(
                    url=url,
                    final_url=current_url,
                    http_status=status_code,
                    status_classification=status_class,
                    has_https=current_url.startswith("https://"),
                    html_content=html_text,
                    response_time_ms=elapsed_ms,
                    error_message=None if status_class == "Website Found" else f"Returned HTTP {status_code}",
                )

            except requests.exceptions.SSLError as e:
                return WebsiteCheckResult(
                    url=url,
                    final_url=current_url,
                    status_classification="Website Check Failed",
                    error_message=f"SSL Certificate Verification Failed: {str(e)}",
                )
            except requests.exceptions.Timeout:
                return WebsiteCheckResult(
                    url=url,
                    final_url=current_url,
                    status_classification="Website Inaccessible",
                    error_message=f"Connection timed out after {self.timeout} seconds.",
                )
            except requests.exceptions.ConnectionError as e:
                return WebsiteCheckResult(
                    url=url,
                    final_url=current_url,
                    status_classification="Website Inaccessible",
                    error_message=f"Connection refused or host unreachable: {str(e)}",
                )
            except Exception as e:
                return WebsiteCheckResult(
                    url=url,
                    final_url=current_url,
                    status_classification="Website Check Failed",
                    error_message=f"Request error: {str(e)}",
                )

        return WebsiteCheckResult(
            url=url,
            final_url=current_url,
            status_classification="Website Check Failed",
            error_message=f"Exceeded maximum redirect limit of {self.max_redirects} hops.",
        )

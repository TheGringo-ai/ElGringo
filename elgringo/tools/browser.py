"""
Browser Tools - Web automation for AI agents
=============================================

Capabilities:
- Fetch web pages
- Extract content
- Search the web
- Take screenshots
- Fill forms (with permission)
"""

import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

from .base import Tool, ToolResult, PermissionManager

logger = logging.getLogger(__name__)


class BrowserTools(Tool):
    """
    Browser automation tools.

    Uses httpx for simple fetches and Playwright for full automation.
    """

    # Domains that are always allowed
    SAFE_DOMAINS = [
        "github.com", "stackoverflow.com", "docs.python.org",
        "developer.mozilla.org", "pypi.org", "npmjs.com",
    ]

    # User agent for requests
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AIDevTeam/1.0"

    def __init__(self, permission_manager: Optional[PermissionManager] = None):
        super().__init__(
            name="browser",
            description="Browse the web, fetch pages, and extract content",
            permission_manager=permission_manager,
        )

        # Register operations
        self.register_operation("fetch", self._fetch_page, "Fetch a web page")
        self.register_operation("extract", self._extract_content, "Extract specific content from URL")
        self.register_operation("search", self._web_search, "Search the web")
        self.register_operation("screenshot", self._take_screenshot, "Take a screenshot of a page")
        self.register_operation("links", self._extract_links, "Extract all links from a page")
        self.register_operation("tables", self._extract_tables, "Extract tables from a page")

        self._playwright = None
        self._browser = None

    def _is_safe_domain(self, url: str) -> bool:
        """Check if URL is from a safe domain"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return any(safe in domain for safe in self.SAFE_DOMAINS)
        except Exception:
            return False

    async def _get_httpx_client(self):
        """Get httpx client for simple requests"""
        import httpx
        return httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": self.USER_AGENT},
            follow_redirects=True,
        )

    async def _fetch_page(
        self,
        url: str,
        extract_text: bool = True,
        include_html: bool = False,
        max_length: int = 50000
    ) -> ToolResult:
        """Fetch a web page and extract content"""
        try:
            async with await self._get_httpx_client() as client:
                response = await client.get(url)
                response.raise_for_status()

                html = response.text
                result = {
                    "url": str(response.url),
                    "status": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                }

                if include_html:
                    result["html"] = html[:max_length]

                if extract_text:
                    # Extract readable text
                    text = self._html_to_text(html)
                    result["text"] = text[:max_length]
                    result["text_length"] = len(text)

                return ToolResult(
                    success=True,
                    output=result,
                    metadata={"url": url}
                )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to readable text"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Get text
            text = soup.get_text(separator="\n")

            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines()]
            text = "\n".join(line for line in lines if line)

            return text

        except ImportError:
            # Fallback: basic regex cleanup
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text)
            return text.strip()

    async def _extract_content(
        self,
        url: str,
        selector: str,
        attribute: Optional[str] = None
    ) -> ToolResult:
        """Extract specific content using CSS selector"""
        try:
            async with await self._get_httpx_client() as client:
                response = await client.get(url)
                response.raise_for_status()

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")

                elements = soup.select(selector)

                results = []
                for el in elements[:50]:  # Limit results
                    if attribute:
                        value = el.get(attribute)
                        if value:
                            results.append(value)
                    else:
                        results.append(el.get_text(strip=True))

                return ToolResult(
                    success=True,
                    output=results,
                    metadata={"url": url, "selector": selector, "count": len(results)}
                )

        except ImportError:
            return ToolResult(success=False, output=None, error="BeautifulSoup not installed: pip install beautifulsoup4")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def _web_search(
        self,
        query: str,
        num_results: int = 5
    ) -> ToolResult:
        """Search the web using duckduckgo-search library (structured, reliable)."""
        try:
            # Try new package name first, fall back to old
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            results = []
            for r in DDGS().text(query, max_results=num_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })

            return ToolResult(
                success=True,
                output=results,
                metadata={"query": query, "count": len(results)}
            )

        except ImportError:
            # Fallback to HTML scraping if neither package installed
            return await self._web_search_fallback(query, num_results)
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}, trying fallback")
            return await self._web_search_fallback(query, num_results)

    async def _web_search_fallback(
        self,
        query: str,
        num_results: int = 5
    ) -> ToolResult:
        """Fallback HTML scraping search if duckduckgo-search is unavailable."""
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={query}"

            async with await self._get_httpx_client() as client:
                response = await client.get(search_url)

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")

                results = []
                for result in soup.select(".result")[:num_results]:
                    title_el = result.select_one(".result__title")
                    link_el = result.select_one(".result__url")
                    snippet_el = result.select_one(".result__snippet")

                    if title_el:
                        results.append({
                            "title": title_el.get_text(strip=True),
                            "url": link_el.get_text(strip=True) if link_el else "",
                            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        })

                return ToolResult(
                    success=True,
                    output=results,
                    metadata={"query": query, "count": len(results)}
                )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def _take_screenshot(
        self,
        url: str,
        output_path: str = "/tmp/screenshot.png",
        full_page: bool = False,
        width: int = 1280,
        height: int = 720
    ) -> ToolResult:
        """Take a screenshot of a web page using Playwright"""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page(viewport={"width": width, "height": height})
                await page.goto(url, wait_until="networkidle")
                await page.screenshot(path=output_path, full_page=full_page)
                await browser.close()

            return ToolResult(
                success=True,
                output={"path": output_path, "url": url},
                metadata={"width": width, "height": height, "full_page": full_page}
            )

        except ImportError:
            return ToolResult(
                success=False, output=None,
                error="Playwright not installed: pip install playwright && playwright install"
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def _extract_links(self, url: str, external_only: bool = False) -> ToolResult:
        """Extract all links from a page"""
        try:
            async with await self._get_httpx_client() as client:
                response = await client.get(url)

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")

                base_domain = urlparse(url).netloc
                links = []

                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full_url = urljoin(url, href)
                    link_domain = urlparse(full_url).netloc

                    is_external = link_domain != base_domain

                    if external_only and not is_external:
                        continue

                    links.append({
                        "text": a.get_text(strip=True)[:100],
                        "url": full_url,
                        "external": is_external,
                    })

                return ToolResult(
                    success=True,
                    output=links[:200],  # Limit results
                    metadata={"url": url, "count": len(links)}
                )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def _extract_tables(self, url: str) -> ToolResult:
        """Extract tables from a web page"""
        try:
            async with await self._get_httpx_client() as client:
                response = await client.get(url)

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")

                tables = []
                for table in soup.find_all("table")[:10]:  # Limit tables
                    rows = []
                    for tr in table.find_all("tr"):
                        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                        if cells:
                            rows.append(cells)
                    if rows:
                        tables.append(rows)

                return ToolResult(
                    success=True,
                    output=tables,
                    metadata={"url": url, "table_count": len(tables)}
                )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def get_capabilities(self) -> List[Dict[str, str]]:
        """Return list of available operations"""
        return [
            {"operation": "fetch", "description": "Fetch a web page and extract text"},
            {"operation": "extract", "description": "Extract content using CSS selector"},
            {"operation": "search", "description": "Search the web"},
            {"operation": "screenshot", "description": "Take a screenshot of a page"},
            {"operation": "links", "description": "Extract all links from a page"},
            {"operation": "tables", "description": "Extract tables from a page"},
        ]

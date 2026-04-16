"""
Scraper for MUI (Material UI) documentation.

Crawls component pages from mui.com/material-ui and saves raw content
as JSON files in data/raw/.
"""

import json
import time
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://mui.com"
MATERIAL_UI_BASE = "https://mui.com/material-ui"

# Sections of MUI docs to scrape
SECTIONS = [
    "/getting-started/overview/",
    "/getting-started/installation/",
    "/getting-started/usage/",
    "/getting-started/example-projects/",
    "/customization/theming/",
    "/customization/palette/",
    "/customization/typography/",
    "/customization/spacing/",
    "/customization/breakpoints/",
    "/customization/css-theme-variables/overview/",
    "/customization/color/",
    "/customization/z-index/",
    "/customization/transitions/",
    "/customization/how-to-customize/",
    "/customization/dark-mode/",
]

# MUI component pages
COMPONENT_PATHS = [
    # Inputs
    "/react-autocomplete/",
    "/react-button/",
    "/react-button-group/",
    "/react-checkbox/",
    "/react-floating-action-button/",
    "/react-radio-button/",
    "/react-rating/",
    "/react-select/",
    "/react-slider/",
    "/react-switch/",
    "/react-text-field/",
    "/react-transfer-list/",
    "/react-toggle-button/",
    # Data display
    "/react-avatar/",
    "/react-badge/",
    "/react-chip/",
    "/react-divider/",
    "/react-icons/",
    "/react-list/",
    "/react-table/",
    "/react-tooltip/",
    "/react-typography/",
    # Feedback
    "/react-alert/",
    "/react-backdrop/",
    "/react-dialog/",
    "/react-progress/",
    "/react-skeleton/",
    "/react-snackbar/",
    # Surfaces
    "/react-accordion/",
    "/react-app-bar/",
    "/react-card/",
    "/react-paper/",
    # Navigation
    "/react-bottom-navigation/",
    "/react-breadcrumbs/",
    "/react-drawer/",
    "/react-link/",
    "/react-menu/",
    "/react-pagination/",
    "/react-speed-dial/",
    "/react-stepper/",
    "/react-tabs/",
    # Layout
    "/react-box/",
    "/react-container/",
    "/react-grid/",
    "/react-grid2/",
    "/react-stack/",
    "/react-image-list/",
    "/react-hidden/",
    # Utils
    "/react-click-away-listener/",
    "/react-css-baseline/",
    "/react-modal/",
    "/react-no-ssr/",
    "/react-popover/",
    "/react-popper/",
    "/react-portal/",
    "/react-textarea-autosize/",
    "/react-transitions/",
    "/react-use-media-query/",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

REQUEST_DELAY = 1.0  # seconds between requests


@dataclass
class ScrapedPage:
    url: str
    title: str
    section: str          # e.g. "component", "customization", "getting-started"
    component_name: str   # e.g. "Button", "TextField", ""
    content: str          # cleaned text content
    headings: list[str]   # h1/h2/h3 headings found on the page
    code_examples: list[str]  # code blocks found on the page


def _clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _extract_component_name(path: str) -> str:
    match = re.search(r"/react-([a-z0-9-]+)/?$", path)
    if match:
        return match.group(1).replace("-", " ").title()
    return ""


def _classify_section(path: str) -> str:
    if path.startswith("/react-"):
        return "component"
    if "getting-started" in path:
        return "getting-started"
    if "customization" in path:
        return "customization"
    return "other"


def scrape_page(url: str, session: requests.Session) -> Optional[ScrapedPage]:
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [WARN] Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # Remove noisy elements
    for tag in soup.select(
        "script, style, nav, footer, header, "
        "[class*='MuiDrawer'], [class*='MuiAppBar'], "
        "[aria-label='breadcrumb'], [class*='ad-'], "
        ".docsearch-content"
    ):
        tag.decompose()

    # Title
    title_tag = soup.find("h1")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""

    # Main content area — MUI docs use <main> or a specific article container
    main = soup.find("main") or soup.find("article") or soup.body
    if main is None:
        return None

    # Headings
    headings = [
        h.get_text(" ", strip=True)
        for h in main.find_all(["h1", "h2", "h3"])
        if h.get_text(strip=True)
    ]

    # Code examples
    code_examples = [
        pre.get_text("\n", strip=True)
        for pre in main.find_all("pre")
        if pre.get_text(strip=True)
    ]

    # Full text (excluding code blocks to avoid noise in main body)
    for pre in main.find_all("pre"):
        pre.decompose()

    content = _clean_text(main.get_text("\n", strip=True))

    parsed = urlparse(url)
    path = parsed.path.replace("/material-ui", "")

    return ScrapedPage(
        url=url,
        title=title,
        section=_classify_section(path),
        component_name=_extract_component_name(path),
        content=content,
        headings=headings,
        code_examples=code_examples,
    )


def build_urls() -> list[tuple[str, str]]:
    """Return list of (url, slug) pairs to scrape."""
    urls = []
    for path in SECTIONS + COMPONENT_PATHS:
        url = urljoin(MATERIAL_UI_BASE, path)
        slug = path.strip("/").replace("/", "_")
        urls.append((url, slug))
    return urls


def scrape_all(output_dir: Path, delay: float = REQUEST_DELAY) -> list[ScrapedPage]:
    output_dir.mkdir(parents=True, exist_ok=True)
    urls = build_urls()
    session = requests.Session()
    pages: list[ScrapedPage] = []

    print(f"Scraping {len(urls)} MUI documentation pages...")
    for url, slug in tqdm(urls, unit="page"):
        out_file = output_dir / f"{slug}.json"
        if out_file.exists():
            with open(out_file) as f:
                data = json.load(f)
            pages.append(ScrapedPage(**data))
            continue

        page = scrape_page(url, session)
        if page:
            with open(out_file, "w") as f:
                json.dump(asdict(page), f, indent=2)
            pages.append(page)

        time.sleep(delay)

    print(f"Scraped {len(pages)} pages successfully.")
    return pages


def load_raw(raw_dir: Path) -> list[ScrapedPage]:
    """Load previously scraped pages from disk."""
    pages = []
    for f in sorted(raw_dir.glob("*.json")):
        with open(f) as fh:
            pages.append(ScrapedPage(**json.load(fh)))
    return pages

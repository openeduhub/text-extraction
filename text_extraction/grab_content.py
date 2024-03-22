from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any, Literal, Optional

import py3langid as langid
import trafilatura
from playwright import async_api
from trafilatura.settings import use_config

from text_extraction.rate_limiting import get_simple_multibucket_limiter, url_mapper

# limit per-domain accesses to 5 per second and 50 per minute
limiter = get_simple_multibucket_limiter(
    max_rate_per_second=5, base_weight=1
).as_decorator()(url_mapper)
Preference = Literal["none", "recall", "precision"]


@limiter
def from_url(
    url: str, target_language: str = "auto", preference: Preference = "none"
) -> Optional[str]:
    """Extract the text from the given URL"""
    # disable signal, because it causes issues with the web-service
    newconfig = use_config()
    newconfig.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")

    downloaded = trafilatura.fetch_response(url, config=newconfig, decode=True)

    if downloaded is None:
        return None

    return from_binary_html(
        downloaded, target_language=target_language, preference=preference
    )


default_goto = partial(async_api.Page.goto, wait_until="load", timeout=90000)


@limiter  # type: ignore
async def from_headless_browser(
    url: str,
    browser: async_api.Browser,
    target_language: str = "auto",
    preference: Preference = "none",
    goto_fun: Callable[[async_api.Page, str], Awaitable] = default_goto,
) -> Optional[str]:
    # create a new page for this task and close it once we are done
    async with await browser.new_page() as page:
        await goto_fun(page, url)
        content = await page.content()

    if content is None:
        return None

    return from_binary_html(
        content, target_language=target_language, preference=preference
    )


def from_binary_html(
    html: Any, target_language: str = "auto", preference: Preference = "none", **kwargs
) -> Optional[str]:
    """Extract the text from the raw html."""
    fulltext = trafilatura.extract(
        html,
        favor_recall=preference == "recall",
        favor_precision=preference == "precision",
        target_language=target_language if target_language != "auto" else None,
        **kwargs
    )

    # when trafilatura doesn't provide anything, use html2text as a fall-bock
    if fulltext is None:
        fulltext = trafilatura.html2txt(html)

    return fulltext


def get_lang(text: str) -> str:
    lang, _ = langid.classify(text)
    return lang

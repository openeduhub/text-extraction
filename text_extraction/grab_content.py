from functools import partial
from collections.abc import Callable, Awaitable
from typing import Literal, Optional, Any

from playwright import async_api
import py3langid as langid
import trafilatura
from trafilatura.settings import use_config

Preference = Literal["none", "recall", "precision"]


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


async def from_headless_browser(
    browser: async_api.Browser,
    url: str,
    target_language: str = "auto",
    preference: Preference = "none",
    goto_fun: Callable[[async_api.Page, str], Awaitable] = default_goto,
) -> Optional[str]:
    page = await browser.new_page()
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

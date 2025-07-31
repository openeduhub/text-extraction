from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any, Literal, Optional

import py3langid as langid
import requests
import trafilatura
from playwright import async_api
from pydantic import BaseModel
from trafilatura.settings import use_config

from text_extraction.rate_limiting import get_simple_multibucket_limiter, domain_mapper


class GrabbedContent(BaseModel):
    fulltext: str | None = None
    status: int


class FailedContent(BaseModel):
    content: str | None = None
    reason: str
    status: int


# limit per-domain accesses to 5 per second and 50 per minute
limiter = get_simple_multibucket_limiter(
    max_rate_per_second=5, base_weight=1
).as_decorator()(domain_mapper)

# Preference settings control the trafilatura.extract() core function
# https://trafilatura.readthedocs.io/en/latest/corefunctions.html#extraction
Preference = Literal["none", "recall", "precision"]


def from_html_unlimited(
    url: str,
    target_language: str = "auto",
    preference: Preference = "none",
    output_format="txt",
) -> GrabbedContent | FailedContent:
    """Extract the text from the given URL"""
    # disable signal, because it causes issues with the web-service
    newconfig = use_config()
    newconfig.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")

    downloaded = trafilatura.fetch_response(url, config=newconfig, decode=True)
    if downloaded is None:
        _text = None
        # if trafilatura can't fetch a response, it returns None.
        # to at least get a rough idea of what went wrong, a fallback HTTP GET via ``requests`` is made.
        _response = requests.get(url)
        if _response.ok:
            # happy case: if the HTTP status is between 200 and 400
            _text = from_binary_html(
                _response.content,
                target_language=target_language,
                preference=preference,
                output_format=output_format,
            )
            grabbed_content: GrabbedContent = GrabbedContent(
                fulltext=_text,
                status=_response.status_code,
            )
            return grabbed_content
        else:
            # sad case: the HTTP response indicates an error
            failed_content: FailedContent = FailedContent(
                content=_response.content,
                reason=_response.reason,
                status=_response.status_code,
            )
            return failed_content
    else:
        _text = from_binary_html(
            downloaded,
            target_language=target_language,
            preference=preference,
            output_format=output_format,
        )
        grabbed_content: GrabbedContent = GrabbedContent(
            fulltext=_text,
            status=downloaded.status,
        )
        return grabbed_content


from_html = limiter(from_html_unlimited)

default_goto = partial(async_api.Page.goto, wait_until="load", timeout=90000)


async def from_headless_browser_unlimited(
    url: str,
    browser: async_api.Browser,
    target_language: str = "auto",
    preference: Preference = "none",
    output_format="txt",
    goto_fun: Callable[[async_api.Page, str], Awaitable] = default_goto,
) -> GrabbedContent | FailedContent:
    # create a new page for this task and close it once we are done
    async with await browser.new_page() as page:
        response = await goto_fun(page, url)
        content = await page.content()

        if response.ok is False:
            failed_content: FailedContent = FailedContent(
                content=content, status=response.status, reason=response.status_text
            )
            return failed_content
        else:
            _fulltext = from_binary_html(
                content,
                target_language=target_language,
                preference=preference,
                output_format=output_format,
            )
            grabbed_content: GrabbedContent = GrabbedContent(
                fulltext=_fulltext,
                status=response.status,
            )
            return grabbed_content


from_headless_browser = limiter(from_headless_browser_unlimited)  # type: ignore


def from_binary_html(
    html: Any,
    target_language: str = "auto",
    preference: Preference = "none",
    output_format="txt",
    **kwargs,
) -> Optional[str]:
    """Extract the text from the raw html."""
    # ToDo:
    #  - markdown conversion for binary files via MarkItDown (instead of trafilatura)
    fulltext = trafilatura.extract(
        html,
        favor_recall=preference == "recall",
        favor_precision=preference == "precision",
        output_format=output_format,
        target_language=target_language if target_language != "auto" else None,
        **kwargs,
    )

    # when trafilatura doesn't provide anything, use html2text as a fall-bock
    if fulltext is None:
        fulltext = trafilatura.html2txt(html)

    return fulltext


def get_lang(text: str) -> str:
    lang, _ = langid.classify(text)
    return lang

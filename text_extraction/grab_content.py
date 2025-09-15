from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any, Literal, Optional

import py3langid as langid
import requests
import trafilatura
from playwright import async_api
from playwright.async_api import Error
from trafilatura.settings import use_config
from trafilatura.readability_lxml import is_probably_readerable

from text_extraction.fake_user_agent import GENERATED_USER_AGENT
from text_extraction.markitdown_helper import (
    fetch_markdown_from_html_content,
    fetch_markdown_from_url,
)
from text_extraction.models import GrabbedContent, FailedContent
from text_extraction.rate_limiting import get_simple_multibucket_limiter, domain_mapper

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
    # set a somewhat recent User-Agent (to reduce the number of "your browser is too old" errors)
    newconfig.set("DEFAULT", "USER_AGENTS", GENERATED_USER_AGENT)

    downloaded = trafilatura.fetch_response(url, config=newconfig, decode=True)
    if downloaded is None:
        _text = None
        # if trafilatura can't fetch a response, it returns None.
        # to at least get a rough idea of what went wrong, a fallback HTTP GET via ``requests`` is made.
        _user_agent_header = {"User-Agent": GENERATED_USER_AGENT}
        _response = requests.get(url=url, headers=_user_agent_header)
        _is_readable = is_probably_readerable(_response.content)
        if _response.ok and _is_readable:
            # happy case: if the HTTP status is between 200 and 400
            match output_format:
                case "txt" | "html" | "markdown":
                    _text = extract_from_binary_html_with_trafilatura(
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
                case _:
                    failed_content: FailedContent = FailedContent(
                        content=_response.content,
                        reason="Unsupported output format.",
                        status=_response.status_code,
                    )
                    return failed_content
        else:
            # sad case: the HTTP response indicates an error
            failed_content: FailedContent = FailedContent(
                content=_response.content,
                reason=_response.reason,
                status=_response.status_code,
            )
            return failed_content
    else:
        _text = extract_from_binary_html_with_trafilatura(
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
    async with await browser.new_page(user_agent=GENERATED_USER_AGENT) as page:
        try:
            _response = await goto_fun(page, url)
        except Error as playwright_error:
            if "Download is starting" in str(playwright_error):
                # this case happens when a website triggers a file download (e.g.: the URl points to a PDF file)
                extracted_content = fetch_markdown_from_url(url)
                return extracted_content
            else:
                raise playwright_error
        _body = await _response.body()
        # guess if the response contains a valid text corpus.
        # (trafilatura uses a backported function of Mozilla's readability.js to detect common indicators of text content)
        _is_readable = is_probably_readerable(_body)
        _content = await page.content()

        if not _response.ok:
            # sad case: the HTTP response indicates an error (and we don't want to parse 404 tombstone pages!)
            failed_content: FailedContent = FailedContent(
                content=_content, status=_response.status, reason=_response.status_text
            )
            return failed_content
        elif _is_readable:
            # happy case: the HTTP response indicates a valid text corpus that trafilatura can handle
            match output_format:
                case "txt" | "html":
                    # handle "txt" and "html" requests with trafilatura
                    _fulltext = extract_from_binary_html_with_trafilatura(
                        _content,
                        target_language=target_language,
                        preference=preference,
                        output_format=output_format,
                    )
                    grabbed_content: GrabbedContent = GrabbedContent(
                        fulltext=_fulltext,
                        status=_response.status,
                    )
                    return grabbed_content
                case "markdown":
                    _fulltext = fetch_markdown_from_html_content(_content)
                    grabbed_content: GrabbedContent = GrabbedContent(
                        fulltext=_fulltext,
                        status=_response.status,
                    )
                    return grabbed_content
                case _:
                    failed_content: FailedContent = FailedContent(
                        content=_content,
                        reason="Unsupported output format.",
                        status=_response.status,
                    )
                    return failed_content
        else:
            # sad case: the HTTP response appears to be ok, but the text corpus isn't readable by trafilatura
            failed_content: FailedContent = FailedContent(
                content=_content,
                reason="No text content found.",
                status=_response.status,
            )
            return failed_content


from_headless_browser = limiter(from_headless_browser_unlimited)  # type: ignore


def extract_from_binary_html_with_trafilatura(
    html: Any,
    target_language: str = "auto",
    preference: Preference = "none",
    output_format="txt",
    **kwargs,
) -> Optional[str]:
    """Extract the text from the raw html."""
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

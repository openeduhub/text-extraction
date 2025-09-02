#!/usr/bin/env python3
import argparse
from datetime import datetime
from enum import StrEnum, auto
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from playwright import async_api
from pydantic import BaseModel, Field

import text_extraction.grab_content as grab_content
from text_extraction._version import __version__
from text_extraction.grab_content import GrabbedContent, FailedContent
from text_extraction.markitdown_helper import fetch_markdown_from_url

app = FastAPI()


class HealthCheck(BaseModel):
    status: str = "ok"
    version: str = __version__
    timestamp: datetime = Field(default_factory=datetime.now)


class Methods(StrEnum):
    simple = auto()
    browser = auto()


class OutputFormats(StrEnum):
    txt = auto()
    markdown = auto()
    html = auto()


class Data(BaseModel):
    url: str
    method: Methods = Methods.simple
    browser_location: Optional[str] = Field(default=None, examples=[None])
    lang: str = "auto"
    output_format: str = OutputFormats.txt
    preference: grab_content.Preference = "none"


class ExtractionResult(BaseModel):
    text: str
    lang: str
    status: int | None = Field(
        description="HTTP status code of the target website.", examples=[200, 301]
    )
    version: str = __version__


class FailedExtraction(BaseModel):
    error_message: str = Field(
        default="No content was extracted.",
    )
    status: int | None = Field(
        description="HTTP status code of the target website ", examples=[404, 503]
    )
    reason: str | None = Field(
        description="HTTP reason of the target website. "
        "Only available if the website status indicated an error.",
        examples=["Not Found", "Service Unavailable"],
        default=None,
    )
    version: str = __version__
    content: str | None = Field(
        default=None,
        description="The response content of the target website. ",
        examples=["<html>...", "</html>"],
    )

    class Config:
        # this config makes sure that the HTTP Exception with status 424 appears in the openapi.json
        json_schema_extra = {
            "example": {
                "error_message": "No content was extracted from the target website.",
                "status": 404,
                "reason": "Not Found",
                "version": __version__,
                "content": "<html>...",
            }
        }


@app.get("/_ping")
async def _ping() -> HealthCheck:
    return HealthCheck()


summary = "Extract text from a given URL"


@app.post(
    "/from-url",
    summary=summary,
    description=f"""
    {summary}

    Parameters
    ---------
    url : str
        The URL from which to extract text.
    lang : str, optional
        The ISO 639-1 code for the language of the text.
        If set to 'auto', try to detect it instead.
        Default: 'auto'.
    preference : str, optional
        Whether to prioritize precision, recall, or neither
        when extracting the text.
        Default: 'none'
    method : "simple" or "browser"
        Whether to get the content of the website naively, or to use a headless
        browser in order to e.g. deal with JavaScript-heavy pages.
    output_format : "txt" or "markdown" or "html"
        txt: plain text (via trafilatura)
        markdown: text in markdown format (via MarkItDown)
        html: cleaned HTML (via trafilatura)

    Returns
    -------
    text : str
        The extracted text.
    lang : str
        If lang was set to 'auto', the detected language.
        Otherwise, whatever lang was set to.
    version : str
        The version of the text extractor.
    status: int
        The HTTP status code of the target website.
    """,
    responses={
        status.HTTP_200_OK: {"model": ExtractionResult},
        status.HTTP_424_FAILED_DEPENDENCY: {
            "model": FailedExtraction,
            "description": "Failed Dependency: No content could be extracted from the target website.",
        },
    },
)
async def from_url(request: Request, data: Data) -> ExtractionResult:
    """Extract text from a given URL"""
    _content, _reason, _status, _text = None, None, None, None
    lang = data.lang

    # ToDo: stabilize binary file extraction for "text" and "html" output formats
    extracted_content: GrabbedContent | FailedContent | None = None
    if data.output_format == OutputFormats.markdown:
        # markitdown extraction takes priority since it uses a different approach (via MarkItDown).
        # it can handle more file extensions than the other output formats (which use trafilatura)
        extracted_content: GrabbedContent | FailedContent = fetch_markdown_from_url(
            url=data.url
        )
    # the simple method is, as its name suggests, pretty simple to use
    elif data.method == Methods.simple:
        extracted_content: GrabbedContent | FailedContent = grab_content.from_html(
            data.url,
            preference=data.preference,
            target_language=lang,
            output_format=data.output_format,
        )

    # using a headless browser requires us to specify the browser to use.
    # if no cdp location was given, just start up a new one.
    else:
        if data.browser_location is None:
            # use a local browser instance
            async with async_api.async_playwright() as p:
                browser = await p.chromium.launch(
                    args=[
                        # HACK: for some reason, passing this avoids an issue where
                        # text extraction would fail when the service is run within
                        # Docker, due to a page crash
                        "--single-process"
                    ]
                )
                extracted_content = await grab_content.from_headless_browser(
                    data.url,
                    browser=browser,
                    preference=data.preference,
                    target_language=lang,
                    output_format=data.output_format,
                )
        else:
            # connect to an existing browser instance (e.g.: a headless browser within a docker container)
            async with async_api.async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(
                    endpoint_url=data.browser_location
                )
                extracted_content = await grab_content.from_headless_browser(
                    data.url,
                    browser=browser,
                    preference=data.preference,
                    target_language=lang,
                    output_format=data.output_format,
                )

    if extracted_content is not None:
        if isinstance(extracted_content, FailedContent):
            # sad case: text extraction failed
            _text = None
            _content = extracted_content.content
            _reason = extracted_content.reason
            _status = extracted_content.status
        if isinstance(extracted_content, GrabbedContent):
            # happy case: text extraction succeeded
            _text = extracted_content.fulltext
            _status = extracted_content.status

    # no content could be grabbed -> raise an exception
    if _text is None:
        if data.lang is None:
            language_line = "or because the language was not succesfully detected. Try setting the lang parameter."
        elif _status != 200:
            language_line = (
                f"or because the website returned an error status code {_status}."
            )
        else:
            language_line = f"or because the text is not of language '{lang}'."

        failed_extraction = FailedExtraction(
            error_message=f"No content was extracted. "
            f"This could be due to no text being present on the page, the website relying on JavaScript, "
            f"{language_line}",
            status=_status,
            reason=_reason,
            content=_content,
        )
        raise HTTPException(
            status_code=424,
            detail=failed_extraction.model_dump(),
        )

    lang = lang if lang != "auto" else grab_content.get_lang(_text)

    return ExtractionResult(text=_text, lang=lang, status=_status)


def main():
    # define CLI arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", action="store", default=8080, help="Port to listen on", type=int
    )
    parser.add_argument(
        "--host", action="store", default="0.0.0.0", help="Hosts to listen on", type=str
    )
    parser.add_argument(
        "--lang",
        action="store",
        default="de_DE",
        help="The language of the input text",
        type=str,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )

    # read passed CLI arguments
    args = parser.parse_args()

    # create and run the web service
    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()

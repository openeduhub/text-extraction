#!/usr/bin/env python3

import argparse
from typing import Optional, Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import text_extraction.grab_content as grab_content
from text_extraction._version import __version__

app = FastAPI()


class Data(BaseModel):
    url: str
    preference: grab_content.Preference = None
    lang: Optional[str] = None


class Result(BaseModel):
    text: str
    version: str = __version__


@app.get("/_ping")
async def _ping():
    pass


@app.post("/from-url")
async def from_url(data: Data) -> Result:
    """Extract text from a given URL"""

    text = grab_content.from_url(
        data.url,
        preference=data.preference,
        target_language=data.lang,
    )

    # no content could be grabbed
    if text is None:
        if data.lang is None:
            language_line = "or because the language was not succesfully detected. Try setting the lang parameter."
        else:
            language_line = f"or because the text is not of language {data.lang}."

        raise HTTPException(
            status_code=500,
            detail=f"URL could not be parsed. This could be due to the website relying on JavaScript, {language_line}",
        )

    return Result(text=text)


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

import re
from collections import namedtuple
from os.path import splitext
from urllib.parse import urlparse

import requests
from loguru import logger
from markitdown import MarkItDown

from text_extraction.grab_content import GrabbedContent, FailedContent

# ToDo: currently unsupported document formats:
#  - .odt (Text)
#  - .ods (Spreadsheet)
#  - .odp (Presentation)

# ToDo: most formats are disabled (for now) since they require a LLM Client!
# important: longer file extensions (e.g. .docx) have higher priority than shorter ones (e.g. .doc)
# DO NOT change the order of the following dictionary in a way where
# shorter file extensions are listed before longer ones!
MARKITDOWN_SUPPORTED_FORMATS = {
    # --- Documents ---
    "csv": "Comma-Separated Values",
    "docx": "Microsoft Word Document",
    "doc": "Microsoft Word Document (Legacy)",
    "epub": "Electronic Publication",
    "pdf": "PDF Document",
    "pptx": "Microsoft PowerPoint Presentation",
    "ppt": "Microsoft PowerPoint Presentation (Legacy)",
    "rtf": "Rich Text Format",
    "txt": "Plain Text",
    "xlsx": "Microsoft Excel Spreadsheet",
    "xls": "Microsoft Excel Spreadsheet (Legacy)",
    # --- Images ---
    # ToDo: image captions / descriptions require an LLM client!
    # "jpg": "JPEG Image",
    # "jpeg": "JPEG Image",
    # "png": "PNG Image",
    # "gif": "GIF Image",
    # "bmp": "Bitmap Image",
    # "tiff": "TIFF Image",
    # "tif": "TIFF Image",
    # "svg": "SVG Vector Image",
    # "webp": "WebP Image",
    # --- Audio/Video (with transcription) ---
    # ToDo: audio and video captions / descriptions require an LLM client!
    # "mp3": "MP3 Audio",
    # "wav": "WAV Audio",
    # "mp4": "MP4 Video",
    # "avi": "AVI Video",
    # "mov": "QuickTime Video",
    # "mkv": "Matroska Video",
    # "wmv": "Windows Media Video",
    # "flv": "Flash Video",
    # "webm": "WebM Video",
    # "m4a": "M4A Audio",
    # "aac": "AAC Audio",
    # "ogg": "OGG Audio",
    # "flac": "FLAC Audio",
    # --- Web formats ---
    "html": "HTML Document",
    "htm": "HTML Document",
    "xml": "XML Document",
    "md": "Markdown Document",
    "markdown": "Markdown Document",
    # --- Email formats ---
    "eml": "Email Message",
    "msg": "Outlook Message",
    # --- Archives (limited support) ---
    # "zip": "ZIP Archive",
}

# ToDo: unsupported Document MIME types:
#   OpenDocument formats
#       "application/vnd.oasis.opendocument.text",  # .odt
#       "application/vnd.oasis.opendocument.presentation",  # .odp
#       "application/vnd.oasis.opendocument.spreadsheet",  # .ods
# for reference: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/MIME_types/Common_types
MARKITDOWN_SUPPORTED_CONTENT_MIME_TYPES: set[str] = {
    # PDF formats
    "application/pdf",
    # Word formats
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/msword",  # .doc
    # Excel formats
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",  # .xls
    # PowerPoint formats
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/vnd.ms-powerpoint",  # .ppt
    # RTF and other text formats
    "application/rtf",
    "text/rtf",
    "text/plain",
    "text/html",
    # EPUB format
    "application/epub+zip",
    # CSV format
    "text/csv",
    # fallback values when a webserver doesn't return a complete MIME type
    "pdf",
    "docx",
    "xlsx",
    "pptx",
    "doc",
    "xls",
    "ppt",
    "csv",
}


def _detect_file_extension_in_url_path(url: str) -> str | None:
    # this most basic implementation only works for URLs with a file extension that are separated by a dot.
    _file_extension: str | None = None
    if "." in url:
        _parsed_url = urlparse(url).path
        _file_extension_part: str = splitext(_parsed_url)[1]
        for _supported_file_extension in MARKITDOWN_SUPPORTED_FORMATS.keys():
            if _supported_file_extension in _file_extension_part:
                _file_extension = _supported_file_extension
                logger.debug(f"Detected file extension in URL: {_file_extension}")
                break
        return _file_extension
    else:
        logger.debug(f"No file extension found in URL: {url}")
        return None


def _detect_file_extension_in_content_disposition_header(
    content_disposition: str,
) -> str | None:
    # filenames in Content-Disposition headers are usually surrounded by quotes.
    # see: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Disposition#syntax
    # examples:
    # Content-Disposition: attachment; filename="file name.jpg"
    # Content-Disposition: attachment; filename*=UTF-8''file%20name.jpg
    if "filename" in content_disposition:
        _filename_pattern = re.compile(
            r"""filename[*]?=(?:UTF-8\'\')?"?(?P<filename>([^"\r\n]+))"?"""
        )
        _match = _filename_pattern.search(content_disposition)
        if _match:
            _filename = _match.group("filename")
            logger.debug(
                f"Detected filename in Content-Disposition header: {_filename}"
            )
            if "." in _filename:
                _file_extension = splitext(_filename)[1]
                return _file_extension
    return None


MarkItDownCompatible = namedtuple(
    "MarkItDownCompatible", ["supported_by_markitdown", "http_status_code"]
)


def _determine_markitdown_compatibility(url: str) -> MarkItDownCompatible:
    # check the Content-Type header (as it's the most reliable way to detect the file extension) first
    # ToDo (inaccurate/risky): guess the file extension by using the response content (e.g. via magic bytes)?
    _is_compatible: bool = False

    # fire a HEAD request (to safe traffic) and check the content-type header
    # ToDo: some websites might not return a valid Response via HEAD requests -> fallback to GET request?
    # ToDo: rate-limiting might be necessary here!
    _request_head: requests.Response = requests.head(url)
    _status_code: int = _request_head.status_code
    if _request_head.ok:
        # checking the Content-Type header only makes sense if the HTTP status code is in the >= 200 and < 400 range
        if "Content-Type" in _request_head.headers:
            # first we take a look at the Content-Type Header because it's usually more reliable than the file extension
            _content_type: str = _request_head.headers["Content-Type"]
            if _content_type in MARKITDOWN_SUPPORTED_CONTENT_MIME_TYPES:
                # this detection will not work for websites that return a generic
                # "application/octet-stream" content-type while embedding/rendering the binary file in the DOM
                logger.debug(
                    f"Supported content-type in URL {url} detected: {_content_type}"
                )
                _is_compatible = True
        if "Content-Disposition" in _request_head.headers:
            # some websites might provide a filename in the Content-Disposition header,
            # which could be used as an indicator for the file extension
            _content_disposition: str = _request_head.headers["Content-Disposition"]
            if "filename" in _content_disposition:
                _extension_with_dot: str | None = (
                    _detect_file_extension_in_content_disposition_header(
                        _content_disposition
                    )
                )
                # to compare the file extension with the supported keys from the dict, we need to remove the leading dot
                if (
                    _extension_with_dot
                    and _extension_with_dot.lstrip(".")
                    in MARKITDOWN_SUPPORTED_FORMATS.keys()
                ):
                    logger.debug(
                        f"Detected file extension in Content-Disposition header: {_extension_with_dot}"
                    )
                    _is_compatible = True

    _result = MarkItDownCompatible(
        supported_by_markitdown=_is_compatible,
        http_status_code=_status_code,
    )
    return _result


def _fetch_markdown_from_url(
    url: str, mark_it_down_compatible=MarkItDownCompatible
) -> GrabbedContent | FailedContent:
    _md_converter = MarkItDown()
    try:
        _md_result = _md_converter.convert(url)
        grabbed_content: GrabbedContent = GrabbedContent(
            fulltext=_md_result.markdown,
            status=mark_it_down_compatible.http_status_code,
        )
        return grabbed_content
    except Exception as e:
        logger.error(f"Markdown conversion failed for URL {url}. \nReason: {e}")
        _failed_content: FailedContent = FailedContent(
            content=None,
            reason=f"MarkItDown conversion failed. \n Website target provided the following reason: {e}",
            status=mark_it_down_compatible.http_status_code,
        )
        return _failed_content


def fetch_markdown_from_url(url: str) -> GrabbedContent | FailedContent:
    _is_file_extension_supported: MarkItDownCompatible = (
        _determine_markitdown_compatibility(url)
    )
    _result: GrabbedContent | FailedContent = _fetch_markdown_from_url(
        url=url,
        mark_it_down_compatible=_is_file_extension_supported,
    )
    return _result


# ToDo: implement functions for
#  - implement markitdown function in webservice.py
#   - rate-limit markitdown so it doesn't hammer websites with too many requests at the same time

if __name__ == "__main__":
    test_headers = [
        "inline",
        'attachment; filename="report_2025-08-07.pdf"',
        "attachment; filename=report_2025-08-07.pdf",
        "attachment; filename*=UTF-8''%E6%96%87%E6%A1%A3.txt",
        'inline; filename="image (copy).jpg"',
    ]
    for header in test_headers:
        logger.debug(
            f"{header} -> {_detect_file_extension_in_content_disposition_header(header)}"
        )
    pass

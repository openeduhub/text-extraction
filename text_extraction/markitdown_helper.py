from os.path import splitext
from urllib.parse import urlparse

import requests
from loguru import logger
from markitdown import MarkItDown

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
MARKITDOWN_SUPPORTED_CONTENT_MIME_TYPES = [
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
]


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


def file_extension_is_supported_by_markitdown(url: str) -> bool:
    # 1) check if the URL path indicates a file extension
    # 2) if not: check the content-type header
    # ToDo (inaccurate/risky): 3) guess the file extension by using the response content (e.g. via magic bytes)
    _file_extension_in_url_path = _detect_file_extension_in_url_path(url)
    if _file_extension_in_url_path:
        return True
    else:
        # fire a HEAD request (to safe traffic) and check the content-type header
        # ToDo: some websites might not return a valid Response via HEAD requests -> fallback to GET request?
        # ToDo: rate-limiting might be necessary here!
        _request_head = requests.head(url)
        if "Content-Type" in _request_head.headers:
            _content_type = _request_head.headers["Content-Type"]
            for _supported_content_mime_type in MARKITDOWN_SUPPORTED_CONTENT_MIME_TYPES:
                # this detection will not work for websites that return a generic
                # "application/octet-stream" content-type while embedding/rendering the binary file in the DOM
                if _supported_content_mime_type in _content_type:
                    logger.debug(
                        f"Supported content-type in URL {url} detected: {_content_type}"
                    )
                    return True
    return False


def convert_to_markdown(url: str) -> str | None:
    _md_converter = MarkItDown()
    try:
        _md_result = _md_converter.convert(url)
        return _md_result.markdown
    except Exception as e:
        logger.error(f"Markdown conversion failed for URL {url}. \nReason: {e}")
        return None


# ToDo: implement functions for
#  - retrieve binary files directly with markitdown
#  - implement markitdown function in webservice.py
#   - rate-limit markitdown so it doesn't hammer websites with too many requests at the same time

if __name__ == "__main__":
    url_testcases = [
        "https://www.example.com/example.pdf",
        "https://www.example.com/example.docx",
        "https://www.example.com/example.docx?download=full",
        # "https://ocw.mit.edu/courses/esd-290-special-topics-in-supply-chain-management-spring-2005/060a50539c55fd852582f0ac63844a3e_berniehogan.pdf",
        # "https://www.zoerr.de/edu-sharing/eduservlet/download?nodeId=2c9d9f08-3caa-4bd6-bf4b-0c9b5fb0aacc",
    ]
    for url_testcase in url_testcases:
        file_extension_is_supported = file_extension_is_supported_by_markitdown(
            url_testcase
        )
    convert_to_markdown(
        url="https://www.umwelt-im-unterricht.de/hintergrund/umweltpolitik-in-der-ddr-und-die-entwicklung-seit-der-friedlichen-revolution-1989-1990"
    )
    pass

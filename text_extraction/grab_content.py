from typing import Literal, Optional
import trafilatura
from trafilatura.settings import use_config
import py3langid as langid

Preference = Literal["none", "recall", "precision"]


def from_url(
    url: str, target_language: str = "auto", preference: Preference = "none"
) -> Optional[str]:
    """Extract the text from the given URL"""
    # disable signal, because it causes issues with the web-service
    newconfig = use_config()
    newconfig.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")

    downloaded = trafilatura.fetch_url(url, config=newconfig)

    if downloaded is None:
        return None

    favor_recall, favor_precision = False, False
    if preference == "recall":
        favor_recall = True
    elif preference == "precision":
        favor_precision = True

    text = trafilatura.extract(
        downloaded,
        url=url,
        favor_recall=favor_recall,
        favor_precision=favor_precision,
        target_language=target_language if target_language != "auto" else None,
        config=newconfig,
    )

    return text


def get_lang(text: str) -> str:
    lang, _ = langid.classify(text)
    return lang

from typing import Literal, Optional
import trafilatura
from trafilatura.settings import use_config

Preference = Literal[None, "recall", "precision"]


def from_url(
    url: str, target_language: Optional[str] = None, preference: Preference = None
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

    result = trafilatura.extract(
        downloaded,
        url=url,
        favor_recall=favor_recall,
        favor_precision=favor_precision,
        target_language=target_language,
        config=newconfig,
    )
    return result

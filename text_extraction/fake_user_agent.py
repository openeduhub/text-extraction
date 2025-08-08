from fake_useragent import UserAgent
from loguru import logger


def generate_random_user_agent() -> str:
    """
    Helper method to pick a randomly chosen User-Agent string (from real world data of Chrome browsers).

    :return: A (randomly chosen) User-Agent string (to be used in playwright / scrapy / scrapy-playwright)
    """
    # for reference: https://github.com/fake-useragent/fake-useragent
    _ua = UserAgent(
        browsers=["Chrome"],
        min_version=130.0,
        # some websites show (friendly) notification banners to remind you of upgrading your browser version
        # if the website detects that your browser is too outdated.
        platforms="desktop",
        fallback="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        # this fallback string was manually extracted from 7.5.3735.58 (Stable channel) (64-bit) on 2025-08-08
        os="Linux",
    )
    _user_agent: str = _ua.random
    if _user_agent and isinstance(_user_agent, str):
        return _user_agent
    else:
        return _ua.fallback


if __name__ == "__main__":
    logger.debug(f"Generating random user agent:\n{generate_random_user_agent()}")
    pass

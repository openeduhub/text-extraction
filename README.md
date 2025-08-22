# (kidra) text-extraction

A library and micro-service that utilizes [trafilatura](https://github.com/adbar/trafilatura) and 
[markitdown](https://github.com/microsoft/markitdown) 
in order to extract text from URLs.

While this is currently fairly bare-bones, 
the goal is to provide various improvements on `trafilatura` for our context 
and to provide fall-backs for when extraction fails, 
e.g. due to a heavy reliance on `JavaScript` on the target website.

## Usage as a library

For more customization and control over behavior, 
use the implemented functionality as a native Python library, instead of the provided REST API.

The functions that should be of primary interest are `from_headless_browser_unlimited` and `from_html_unlimited`, 
found in the `text_extraction.grab_content` module.

```python
from text_extraction.grab_content import from_headless_browser_unlimited
from text_extraction.rate_limiting import get_simple_multibucket_limiter, domain_mapper

# limit per-domain accesses to 5 per second and 50 per minute
limiter = get_simple_multibucket_limiter(
    max_rate_per_second=5, base_weight=1
).as_decorator()(domain_mapper)

from_headless_browser_limited = limiter(from_headless_browser_unlimited)
```

# Project setup via `uv`

Please make sure that you have [uv](https://docs.astral.sh/uv/) installed. 
(see: [uv Installation Guide](https://docs.astral.sh/uv/getting-started/installation/))
Before running the project, you can use `uv self update` to fetch the latest version.

```shell
# install the latest Python 3.13 version via uv
uv python install 3.13

# create and activate the virtual environment in the project root (you will see a .venv folder)
uv venv

# Install the project / dependencies
uv sync
```

# Installation as a dependency

## Installation as a dependency via `uv`

```shell
# install the latest version of the project's main branch as a dependency
uv pip install "git+https://github.com/openeduhub/text-extraction.git"

# install the latest version of the develop branch
uv pip install "git+https://github.com/openeduhub/text-extraction.git@develop"

# install a specific version
uv pip install "git+https://github.com/openeduhub/text-extraction.git@v0.3.0"

```

## Installation as a dependency via `pip`

```shell
pip install git+https://github.com/openeduhub/text-extraction.git
```

# Running the service locally

To run the server locally, use the following `uv` shortcut:

```shell
uv run text-extraction --port 8000
```

This shortcut is defined in the `pyproject.toml` file within `[project.scripts]`. *(for reference: [uv Docs: Configuring projects - Command-line interfaces](https://docs.astral.sh/uv/concepts/projects/config/#command-line-interfaces)))*

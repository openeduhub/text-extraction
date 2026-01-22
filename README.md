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

This shortcut is defined in the `pyproject.toml` file within `[project.scripts]`. *(for reference: [uv Docs: Configuring projects - Command-line interfaces](https://docs.astral.sh/uv/concepts/projects/config/#command-line-interfaces))*

# Running the service in Docker

To build and run the service in Docker:

```shell
# Build the Docker image
docker build -t text-extraction:latest .

# Run the container
docker run -p 8000:8000 text-extraction:latest
```

The Dockerfile includes:
- Playwright browser (Chromium) installation during build time
- System dependencies for Chromium runtime
- Optimized layer caching with uv

## Docker Environment Variables

You can customize the service behavior with environment variables:

```shell
docker run -p 8000:8000 \
  -e "PORT=8000" \
  -e "HOST=0.0.0.0" \
  text-extraction:latest
```

# Playwright Browser Dependencies

The service uses [Playwright](https://playwright.dev/) for headless browser automation when the `browser` method is used.

## Local Development

When using the service locally with the `browser` method, you need to install Playwright browsers:

```shell
# Install Chromium browser
playwright install chromium

# Or install all browsers (Chromium, Firefox, WebKit)
playwright install
```

## Docker Deployment

In Docker, Playwright browsers and all required system dependencies are automatically installed during the image build process. No additional setup is required when running the container.

The Dockerfile handles:
1. Installation of system-level dependencies required by Chromium
2. Download of Playwright browser binaries during build time
3. Installation of runtime dependencies via `playwright install-deps`

This ensures the service is ready to use immediately upon container startup.

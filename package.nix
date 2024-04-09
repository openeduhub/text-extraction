# turn the python library into a standalone application, optionally providing
# browsers to playwright
{
  lib,
  toPythonApplication,
  text-extraction,
  playwright-driver,
  includeBrowsers ? true,
}:
toPythonApplication (
  text-extraction.overrideAttrs {
    # optionally provide browsers to playwright
    makeWrapperArgs = lib.lists.optionals includeBrowsers [
      "--set PLAYWRIGHT_BROWSERS_PATH ${playwright-driver.browsers}"
    ];
  }
)

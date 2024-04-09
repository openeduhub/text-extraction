# define and build the python library
{
  buildPythonPackage,
  nix-filter,
  setuptools,
  pandas,
  numpy,
  fastapi,
  uvicorn,
  pydantic,
  trafilatura,
  py3langid,
  playwright,
  pyrate-limiter,
}:

buildPythonPackage {
  pname = "text-extraction";
  version = "0.2.0";
  format = "setuptools";

  # only include files that are related to the application.
  # this will prevent unnecessary rebuilds
  src = nix-filter {
    root = ./.;
    include = [
      "text_extraction"
      ./setup.py
      ./requirements.txt
    ];
    exclude = [ (nix-filter.matchExt "pyc") ];
  };

  propagatedBuildInputs = [
    setuptools
    pandas
    numpy
    fastapi
    uvicorn
    pydantic
    trafilatura
    py3langid
    playwright
    pyrate-limiter
  ];

  # this package has no tests
  doCheck = false;
}

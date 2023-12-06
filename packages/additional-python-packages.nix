{ py-pkgs }:
rec {
  ### build trafilatura & its dependencies from pypi
  htmldate =
    py-pkgs.buildPythonPackage rec {
      pname = "htmldate";
      version = "1.6.0";
      src = py-pkgs.fetchPypi {
        inherit pname version;
        hash = "sha256-WCfI9iahaACinlfoGIo9MtCwjKTHvWYlN7c7u/IsRaY=";
      };
      doCheck = false;
      propagatedBuildInputs = [
        py-pkgs.lxml
        py-pkgs.urllib3
        py-pkgs.dateparser
        py-pkgs.charset-normalizer
      ];
    };

  justext =
    py-pkgs.buildPythonPackage rec {
      pname = "jusText";
      version = "3.0.0";
      src = py-pkgs.fetchPypi {
        inherit pname version;
        sha256 = "7640e248218795f6be65f6c35fe697325a3280fcb4675d1525bcdff2b86faadf";
      };
      doCheck = false;
      propagatedBuildInputs = [
        py-pkgs.lxml
      ];
    };

  courlan =
    py-pkgs.buildPythonPackage rec {
      pname = "courlan";
      version = "0.9.5";
      src = py-pkgs.fetchPypi {
        inherit pname version;
        hash = "sha256-ONw1suO/H11RbQDVGsEuveVD40F8a+b2oic8D8W1s1M=";
      };
      doCheck = false;
      propagatedBuildInputs = [
        py-pkgs.langcodes
        py-pkgs.tld
        py-pkgs.urllib3
      ];
    };

  py3langid =
    py-pkgs.buildPythonPackage rec {
      pname = "py3langid";
      version = "0.2.2";
      src = py-pkgs.fetchPypi {
        inherit pname version;
        sha256 = "b4de01dad7e701f29d216a0935e85e096cc8675903d23ea8445b2bb5f090b96f";
      };
      doCheck = false;
      propagatedBuildInputs = [
        py-pkgs.numpy
      ];
    };

  trafilatura =
    py-pkgs.buildPythonPackage rec {
      pname = "trafilatura";
      version = "1.6.3";
      src = py-pkgs.fetchPypi {
        inherit pname version;
        hash = "sha256-Zx3W4AAOEBxLzo1w9ECLy3n8vyJ17iVZHv4z4sihYA0=";
      };
      doCheck = false;
      propagatedBuildInputs = [
        # required
        py-pkgs.lxml
        py-pkgs.urllib3
        htmldate
        justext
        py-pkgs.certifi
        courlan
        # optional
        py-pkgs.brotli
        py-pkgs.cchardet
        py3langid
        py-pkgs.pycurl
      ];
    };
}

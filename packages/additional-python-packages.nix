{ py-pkgs }:
rec {
  ### build trafilatura & its dependencies from pypi
  charset-normalizer =
    py-pkgs.buildPythonPackage rec {
      pname = "charset-normalizer";
      version = "3.1.0";
      src = py-pkgs.fetchPypi {
        inherit pname version;
        sha256 = "34e0a2f9c370eb95597aae63bf85eb5e96826d81e3dcf88b8886012906f509b5";
      };
      doCheck = false;
      propagatedBuildInputs = [
      ];
    };

  htmldate =
    py-pkgs.buildPythonPackage rec {
      pname = "htmldate";
      version = "1.4.3";
      src = py-pkgs.fetchPypi {
        inherit pname version;
        sha256 = "ec50f084b997fdf6b26f8c31447e5789f4deb71fe69342cda1d7af0c9f91e01b";
      };
      doCheck = false;
      propagatedBuildInputs = [
        py-pkgs.lxml
        py-pkgs.urllib3
        py-pkgs.dateparser
        charset-normalizer
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
      version = "0.9.2";
      src = py-pkgs.fetchPypi {
        inherit pname version;
        sha256 = "c21ac0483a644610e1b706fe7b535503f0a85cfd846f3a42e0fa7061b016127f";
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
      version = "1.5.0";
      src = py-pkgs.fetchPypi {
        inherit pname version;
        sha256 = "7a3e4f8dda70e3dc1f0ae0347fae97355d98233a53a253b6e483ae35681ee781";
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

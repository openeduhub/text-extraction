# various overlays to be applied to nixpkgs, i.e. for adding the python library
# or the standalone application.
{ lib, nix-filter }:
let
  get-python-lib = py-pkgs: py-pkgs.callPackage ./python-lib.nix { inherit nix-filter; };
in
rec {
  default = text-extraction;

  # override some packages from nixpkgs
  fix-nixpkgs = (
    final: prev: {
      pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
        (python-final: python-prev: {
          # the version of pyrate-limiter in nixpkgs is a bit too old
          pyrate-limiter = python-prev.pyrate-limiter.overrideAttrs (oldAttrs: rec {
            version = "3.6.0";
            # the name does not properly update by just changing the version
            name = "${oldAttrs.pname}-${version}";
            src = oldAttrs.src.override {
              rev = "refs/tags/v${version}";
              hash = "sha256-I/wgHVm3QMgt5KEEJnjMj0eH7LTIlNxifKnHqfH4VzA=";
            };
          });
        })
      ];
    }
  );

  # add the python library
  python-lib = lib.composeExtensions fix-nixpkgs (
    final: prev: {
      pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
        (python-final: python-prev: { text-extraction = get-python-lib python-final; })
      ];
    }
  );

  # add the standalone python application (without also adding the python
  # library)
  text-extraction = lib.composeExtensions fix-nixpkgs (
    final: prev:
    let
      # build the python library without adding its dependencies to the global
      # scope of python packages
      text-extraction = get-python-lib final.python3Packages;
      get-app =
        includeBrowsers:
        final.python3Packages.callPackage ./package.nix { inherit text-extraction includeBrowsers; };
    in
    {
      text-extraction = get-app true;
      text-extraction-minimal = get-app false;
    }
  );
}
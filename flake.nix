{
  description = "Extract text from URLs, utilizing Trafilatura";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
    flake-utils.url = "github:numtide/flake-utils";
    nix-filter.url = "github:numtide/nix-filter";
    openapi-checks = {
      url = "github:openeduhub/nix-openapi-checks";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        flake-utils.follows = "flake-utils";
      };
    };
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    {
      # define an overlay to add text-extraction to nixpkgs
      overlays.default = (final: prev: {
        inherit (self.packages.${final.system}) text-extraction;
      });
    } //
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          # enable if unfree packages are required
          config.allowUnfree = false;
        };
        nix-filter = self.inputs.nix-filter.lib;
        openapi-checks = self.inputs.openapi-checks.lib.${system};
        python = pkgs.python310;

        ### list of python packages required to build / run the application
        python-packages-build = py-pkgs:
          with py-pkgs; [
            pandas
            numpy
            uvicorn
            fastapi
            pydantic
            (import ./packages/additional-python-packages.nix
              { inherit py-pkgs; }).trafilatura
            (import ./packages/additional-python-packages.nix
              { inherit py-pkgs; }).py3langid
          ];

        ### list of python packages to include in the development environment
        # the development installation contains all build packages,
        # plus some additional ones we do not need to include in production.
        python-packages-devel = py-pkgs:
          with py-pkgs; [
            ipython
            black
            pyflakes
            isort
          ]
          ++ (python-packages-build py-pkgs);

        ### create the python package
        # the library, parameterized by the python version to use
        text-extraction-library = py-pkgs: py-pkgs.buildPythonPackage {
          pname = "text-extraction";
          version = "0.1.0";
          /*
          only include files that are related to the application
          this will prevent unnecessary rebuilds
          */
          src = nix-filter {
            root = self;
            include = [
              # folders
              "text_extraction"
              "test"
              # files
              ./setup.py
              ./requirements.txt
            ];
            exclude = [ (nix-filter.matchExt "pyc") ];
          };
          propagatedBuildInputs = (python-packages-build py-pkgs);
          # this package has no tests
          doCheck = false;
        };

        # convert the package built above to an application
        # a python application is essentially identical to a python package,
        # but without the importable modules. as a result, it is smaller.
        text-extraction-service =
          python.pkgs.toPythonApplication (text-extraction-library python.pkgs);

      in
      {
        # the packages that we can build
        packages = {
          text-extraction = text-extraction-service;
          default = text-extraction-service;
        };
        # libraries that may be imported
        lib = {
          text-extraction = text-extraction-library;
        };
        # the development environment
        devShells.default = pkgs.mkShell {
          buildInputs = [
            # the development installation of python
            (python.withPackages python-packages-devel)
            # python LSP server
            pkgs.nodePackages.pyright
            # for automatically generating nix expressions, e.g. from PyPi
            pkgs.nix-template
            pkgs.nix-init
          ];
        };
        checks = { } // (nixpkgs.lib.optionalAttrs
          # only run the VM checks on linux systems
          (system == "x86_64-linux" || system == "aarch64-linux")
          {
            openapi-check = (
              openapi-checks.test-service {
                service-bin =
                  "${self.packages.${system}.text-extraction}/bin/text-extraction";
                service-port = 8080;
                openapi-domain = "/openapi.json";
                skip-endpoints = [ "/from-url" ];
              }
            );
          });
      }
    );
}

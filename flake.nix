{
  description = "Extract text from URLs, utilizing Trafilatura";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    nix-filter.url = "github:numtide/nix-filter";
    openapi-checks = {
      url = "github:openeduhub/nix-openapi-checks";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        flake-utils.follows = "flake-utils";
      };
    };
    nix2container.url = "github:nlewo/nix2container";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      ...
    }:
    let
      nix-filter = self.inputs.nix-filter.lib;

      ### list of python packages required to build / run the application
      python-packages-build =
        py-pkgs: with py-pkgs; [
          setuptools
          pandas
          numpy
          fastapi
          uvicorn
          pydantic
          trafilatura
          py3langid
          playwright
          # the version of pyrate-limiter in nixpkgs is old, so override it
          (pyrate-limiter.overrideAttrs (oldAttrs: rec {
            version = "3.6.0";
            # the name does not properly update by just changing the version
            name = "pyrate-limiter-${version}";
            src = oldAttrs.src.override {
              rev = "refs/tags/v${version}";
              hash = "sha256-I/wgHVm3QMgt5KEEJnjMj0eH7LTIlNxifKnHqfH4VzA=";
            };
          }))
        ];

      ### list of python packages to include in the development environment
      # the development installation contains all build packages,
      # plus some additional ones we do not need to include in production.
      python-packages-devel =
        py-pkgs:
        with py-pkgs;
        [
          ipython
          black
          pyflakes
          isort
        ]
        ++ (python-packages-build py-pkgs);

      ### create the python package
      # the library, parameterized by the python version to use
      get-text-extraction-lib =
        py-pkgs:
        py-pkgs.buildPythonPackage {
          pname = "text-extraction";
          version = "0.2.0";
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
      get-text-extraction-app =
        pkgs: py-pkgs:
        py-pkgs.toPythonApplication (
          (get-text-extraction-lib py-pkgs).overrideAttrs (
            finalAttrs: prevAttrs: {
              # provide the browsers for playwright directly through nix
              makeWrapperArgs = [ "--set PLAYWRIGHT_BROWSERS_PATH ${pkgs.playwright-driver.browsers}" ];
            }
          )
        );
    in
    {
      overlays = {
        # add the text-extraction library to nixpkgs
        python-lib = (
          final: prev: {
            pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
              (python-final: python-prev: { text-extraction = get-text-extraction-lib python-final; })
            ];
          }
        );
        # add the webservice to nixpkgs
        default = (final: prev: { text-extraction = self.outputs.packages.${final.system}.default; });
      };
    }
    // flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;
        openapi-checks = self.inputs.openapi-checks.lib.${system};
      in
      {
        # the packages that we can build
        packages = rec {
          text-extraction = get-text-extraction-app pkgs python.pkgs;
          default = text-extraction;
          docker =
            let
              nix2container = self.inputs.nix2container.packages.${system}.nix2container;
            in
            nix2container.buildImage {
              name = "text-extraction";
              tag = "latest";
              config = {
                Cmd = [ "${default}/bin/text-extraction" ];
              };
              # create an empty /tmp directory for playwright
              copyToRoot = pkgs.buildEnv {
                name = "tmp";
                pathsToLink = [ "/tmp" ];
                paths = [
                  (pkgs.runCommand "mk-tmp" { } ''
                    mkdir -p $out/tmp
                  '')
                ];
              };
              maxLayers = 100;
            };
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
            # auto-formatting
            pkgs.nixpkgs-fmt
          ];
        };
        checks =
          { }
          // (nixpkgs.lib.optionalAttrs
            # only run the VM checks on linux systems
            (system == "x86_64-linux" || system == "aarch64-linux")
            {
              openapi-check = (
                openapi-checks.test-service {
                  service-bin = "${self.packages.${system}.text-extraction}/bin/text-extraction";
                  service-port = 8080;
                  openapi-domain = "/openapi.json";
                  skip-endpoints = [ "/from-url" ];
                }
              );
            }
          );
      }
    );
}

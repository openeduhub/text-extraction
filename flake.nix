{
  description = "Extract text from URLs, utilizing Trafilatura";

  inputs = {
    # change to 24.05 once it releases
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
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      nix-filter,
      ...
    }:
    {
      overlays = import ./overlays.nix {
        inherit (nixpkgs) lib;
        nix-filter = nix-filter.lib;
      };
    }
    // flake-utils.lib.eachDefaultSystem (
      system:
      let
        # apply the overlay adding the webservice to this version of nixpkgs
        pkgs = nixpkgs.legacyPackages.${system};
        pkgs-with-app = (pkgs.extend self.outputs.overlays.text-extraction);
        pkgs-with-lib = (pkgs.extend self.outputs.overlays.python-lib);
        openapi-checks = self.inputs.openapi-checks.lib.${system};
      in
      {
        # the packages that we can build
        packages = rec {
          inherit (pkgs-with-app) text-extraction text-extraction-minimal;
          default = text-extraction;
          python-lib = pkgs-with-lib.python3Packages.text-extraction;
        };
        # the development environment
        devShells.default = pkgs-with-lib.callPackage ./shell.nix { };
        checks =
          { }
          // (nixpkgs.lib.optionalAttrs
            # only run the VM checks on linux systems
            (system == "x86_64-linux" || system == "aarch64-linux")
            {
              openapi-check = (
                openapi-checks.test-service {
                  service-bin = "${pkgs-with-app.text-extraction}/bin/text-extraction";
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

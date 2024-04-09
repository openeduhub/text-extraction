{
  mkShell,
  text-extraction,
  python3,
  pyright,
  nix-template,
  nix-init,
  nixfmt,
}:
mkShell {
  packages = [
    (python3.withPackages (
      py-pkgs:
      with py-pkgs;
      [
        ipython
        black
        pyflakes
        isort
      ]
      ++ text-extraction.propagatedBuildInputs
    ))
    pyright
    nix-template
    nix-init
    nixfmt
  ];
}

{
  mkShell,
  python3,
  pyright,
  nix-template,
  nix-init,
  nixfmt,
  nix-tree,
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
        mypy
      ]
      ++ py-pkgs.text-extraction.propagatedBuildInputs
    ))
    pyright
    nix-template
    nix-init
    nixfmt
    nix-tree
  ];
}

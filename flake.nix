{
  description = "extract_otp_secrets dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            python
            pkgs.zbar
            pkgs.git
          ];

          env = {
            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [ pkgs.zbar ];
          } // pkgs.lib.optionalAttrs pkgs.stdenv.hostPlatform.isDarwin {
            DYLD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [ pkgs.zbar ];
          };

          shellHook = ''
            if [ ! -d .venv ]; then
              ${python}/bin/python -m venv .venv
            fi
            source .venv/bin/activate
            pip install -q -U -r requirements.txt
          '';
        };
      });
}

{
  description = "Reproducible Python dev environment with optional CUDA support";

  # ============================================================
  # INPUTS
  # ============================================================

  inputs = rec {
    nixpkgs-stable.url = "github:NixOS/nixpkgs/nixos-25.11";
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";
    nixpkgs = nixpkgs-stable;
    flake-utils.url = "github:numtide/flake-utils";
  };

  # ============================================================
  # OUTPUTS
  # ============================================================

  outputs =
    inputs@{ self
    , nixpkgs
    , nixpkgs-stable
    , nixpkgs-unstable
    , flake-utils
    , ...
    }:
    let
      # ----------------------------------------------------------
      # Toggle: set to false to disable CUDA/NVIDIA dependencies
      # ----------------------------------------------------------
      enableCuda = false;

      mkEnvFromChannel = (nixpkgs-channel:
        flake-utils.lib.eachDefaultSystem (system:
          let
            # ----------------------------------------------------------
            # Package Set Configuration
            # ----------------------------------------------------------

            pkgs = import nixpkgs-channel ({
              inherit system;
              config.allowUnfree = true;
            } // (if enableCuda then {
              config.cudaSupport = true;
              config.cudaVersion = "13";
            } else { }));

            # ----------------------------------------------------------
            # Python Configuration
            # ----------------------------------------------------------

            python3-pkgName = "python313";

            f-python3-devPkgs = (python-pkgs: with python-pkgs; [
              pip
              virtualenv
              tkinter
            ]);

            f-python3-prodPkgs = (python-pkgs: with python-pkgs; [
              # Add your project's Python dependencies here
            ]);

            python3-with-pkgs = pkgs.${python3-pkgName}.withPackages (ps:
              (f-python3-devPkgs ps)
              ++ (f-python3-prodPkgs ps)
            );

            python3-pkgs = pkgs."${python3-pkgName}Packages";

            f-python3Env = (pkgs_:
              pkgs_.${python3-pkgName}.withPackages (ps:
                (f-python3-devPkgs ps)
                ++ (f-python3-prodPkgs ps)
              ));

            f-python3-buildInputs = (pkgs_: with pkgs_; [
              zlib
              glibc
              stdenv.cc.cc.lib
              gcc
              tk
              tcl
              libxcrypt
            ]);

            python3Wrapper = pkgs.writeShellScriptBin "python3" ''
              export LD_LIBRARY_PATH=$NIX_LD_LIBRARY_PATH
              exec ${python3-with-pkgs}/bin/python3 "$@"
            '';

            # ----------------------------------------------------------
            # Graphics / NVIDIA Configuration (conditional on enableCuda)
            # ----------------------------------------------------------

            f-nvidia-buildInputs = (pkgs_: with pkgs_; [
              ffmpeg
              fmt.dev
              libGLU
              libGL
              xorg.libXi
              xorg.libXmu
              freeglut
              xorg.libXext
              xorg.libX11
              xorg.libXv
              xorg.libXrandr
              zlib
              ncurses
              stdenv.cc
              binutils
              wayland
            ]);

            f-nvidia-shellHook = (pkgs_: with pkgs_; ''
              export CMAKE_PREFIX_PATH="${pkgs_.fmt.dev}:$CMAKE_PREFIX_PATH"
              export PKG_CONFIG_PATH="${pkgs_.fmt.dev}/lib/pkgconfig:$PKG_CONFIG_PATH"
              export EXTRA_CCFLAGS="-I/usr/include"
            '');

            # ----------------------------------------------------------
            # Development Shell
            # ----------------------------------------------------------

            devShell = pkgs.mkShell {
              name = "python-dev"; # <-- Rename to your project

              buildInputs =
                (f-python3-buildInputs pkgs)
                ++ (if enableCuda then (f-nvidia-buildInputs pkgs) else [ ]);

              packages = [
                python3Wrapper
                pkgs.uv
                pkgs.mypy
                python3-pkgs.ruff
              ];

              shellHook =
                let
                  tk = pkgs.tk;
                  tcl = pkgs.tcl;
                in
                ''
                  export LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH:$LD_LIBRARY_PATH"
                  export TK_LIBRARY="${tk}/lib/${tk.libPrefix}"
                  export TCL_LIBRARY="${tcl}/lib/${tcl.libPrefix}"

                  ${if enableCuda then (f-nvidia-shellHook pkgs) else ""}

                  if [[ -d .venv ]]; then
                    VENV_PYTHON="$(readlink -f ./.venv/bin/python)"
                    echo "Found .venv/bin/python: $VENV_PYTHON"
                    export PYTHONPATH=".venv/lib/python3.13/site-packages:$PYTHONPATH"
                  fi
                '';

              allowSubstitutes = false;
            };

            # ----------------------------------------------------------
            # FHS Environment
            # For packages requiring traditional Linux filesystem layout
            # ----------------------------------------------------------

            fhsEnv = (pkgs.buildFHSEnv {
              name = "python-fhs-dev"; # <-- Rename to your project

              targetPkgs = (fhs-pkgs:
                let
                  fhs-python3-with-pkgs = f-python3Env fhs-pkgs;
                  fhs-python3-pkgs = fhs-python3-with-pkgs.pkgs;
                in
                [
                  fhs-pkgs.${python3-pkgName}
                  fhs-pkgs.uv
                  fhs-pkgs.mypy
                  fhs-pkgs.git
                  fhs-python3-pkgs.ruff
                ]
                ++ (f-python3-buildInputs fhs-pkgs)
                ++ (if enableCuda then (f-nvidia-buildInputs fhs-pkgs) else [ ])
              );

              multiPkgs = fhs-pkgs: with fhs-pkgs; [
                zlib
                libxcrypt-legacy
              ];

              # profile is a string attr (not a function), so we use the outer
              # pkgs for f-nvidia-shellHook — same package set as fhs-pkgs.
              profile = ''
                export LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH:$LD_LIBRARY_PATH"
                ${if enableCuda then ''
                  export EXTRA_CCFLAGS="-I/usr/include"
                  ${f-nvidia-shellHook pkgs}
                '' else ""}
              '';

              allowSubstitutes = false;
            }).env;

          in
          {
            devShells.default = devShell;
            devShells.build = fhsEnv;
          }
        ));
    in
    mkEnvFromChannel nixpkgs-stable;
}

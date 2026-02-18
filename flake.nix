{
  description = "Aura Protocol: agent tooling, commands, and config sync for Claude Code / OpenCode";

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
      supportedSystems = [ "x86_64-linux" "aarch64-linux" ];

      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system:
        f {
          inherit system;
          pkgs = import nixpkgs { inherit system; };
        }
      );

    in
    {
      # ── Packages ──────────────────────────────────────────────
      packages = forAllSystems ({ pkgs, system }: {
        launch-parallel = pkgs.writeScriptBin "launch-parallel" (
          builtins.replaceStrings
            [ "#!/usr/bin/env python3" ]
            [ "#!${pkgs.python3}/bin/python3" ]
            (builtins.readFile ./launch-parallel.py)
        );

        aura-swarm = pkgs.writeScriptBin "aura-swarm" (
          builtins.replaceStrings
            [ "#!/usr/bin/env python3" ]
            [ "#!${pkgs.python3}/bin/python3" ]
            (builtins.readFile ./aura-swarm)
        );

        default = pkgs.symlinkJoin {
          name = "aura-scripts";
          paths = [
            self.packages.${system}.launch-parallel
            self.packages.${system}.aura-swarm
          ];
        };
      });

      # ── Home Manager Module ──────────────────────────────────
      homeManagerModules = {
        aura-config-sync = import ./nix/hm-module.nix { inherit self; };
      };

      # ── Dev Shell (for working on aura-scripts itself) ───────
      devShells = forAllSystems ({ pkgs, ... }: {
        default = pkgs.mkShell {
          name = "aura-scripts-dev";
          packages = with pkgs; [
            python3
            tmux
          ];
        };
      });
    };
}

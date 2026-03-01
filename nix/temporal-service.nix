/*
  temporal-service.nix — home-manager module for Temporal dev server

  Provides a systemd user service running `temporal server start-dev`.
  Intended for local development; not for production use.

  Usage in home.nix:
    imports = [ inputs.aura-plugins.homeManagerModules.temporal-service ];
    services.temporal-dev-server.enable = true;

  Future extension points (designed but not yet wired):
    - variant = "native": current default (temporal CLI binary)
    - variant = "docker-compose": run via Docker Compose stack
      (add services.temporal-dev-server.dockerComposeFile option)
    - variant = "nix-temporal": nix-packaged temporal binary
      (requires temporal to land in nixpkgs or overlay)
*/

{ config, lib, pkgs, ... }:

let
  cfg = config.services.temporal-dev-server;

  # Common CLI args (port/ui-port are numeric, safe to interpolate unquoted).
  portArgs = [
    "server" "start-dev"
    "--port"     (toString cfg.port)
    "--ui-port"  (toString cfg.uiPort)
  ];

  # Wrapper script: resolve XDG path at runtime and exec temporal (only when dbPath="").
  #
  # Previous approach used ExecStartPre to write an env file + EnvironmentFile to load it,
  # but systemd evaluates EnvironmentFile BEFORE running ExecStartPre, creating a
  # chicken-and-egg failure on every start (the env file lives in RuntimeDirectory tmpfs).
  # Instead, resolve the path inline and exec directly.
  xdgStartScript = pkgs.writeShellScript "temporal-dev-server-start" ''
    set -euo pipefail
    : "''${HOME:?HOME must be set and non-empty}"
    xdg_data_home="''${XDG_DATA_HOME:-''${HOME}/.local/share}"
    db_dir="$xdg_data_home/aura/plugin"
    mkdir -p "$db_dir"
    exec ${cfg.package}/bin/temporal \
      ${lib.concatStringsSep " " portArgs} \
      --namespace ${lib.escapeShellArg cfg.namespace} \
      --db-filename "$db_dir/temporal.db"
  '';

in
{
  # ── Options ─────────────────────────────────────────────────────────────────

  options.services.temporal-dev-server = {

    enable = lib.mkEnableOption "Temporal dev server (systemd user service)";

    port = lib.mkOption {
      type        = lib.types.port;
      default     = 7233;
      description = "gRPC frontend port for the Temporal server.";
      example     = 7233;
    };

    uiPort = lib.mkOption {
      type        = lib.types.port;
      default     = 8233;
      description = "HTTP port for the Temporal Web UI.";
      example     = 8233;
    };

    namespace = lib.mkOption {
      type        = lib.types.str;
      default     = "default";
      description = ''
        Temporal namespace to create and serve.
        Must match TEMPORAL_NAMESPACE used by bin/aurad.py.
      '';
      example     = "aura";
    };

    dbPath = lib.mkOption {
      type        = lib.types.str;
      default     = "";
      description = ''
        Path to SQLite database file for persistence across restarts.
        Empty string (default) auto-resolves to
        ''${XDG_DATA_HOME:-$HOME/.local/share}/aura/plugin/temporal.db
        at service start via a wrapper script (persistent across restarts).
        Set to an explicit path to override the XDG default.
      '';
      example     = "/home/user/.local/share/temporal/temporal.db";
    };

    package = lib.mkOption {
      type        = lib.types.package;
      default     = pkgs.temporal-cli;
      defaultText = lib.literalExpression "pkgs.temporal-cli";
      description = ''
        The temporal CLI package to use. Must provide `temporal` in bin/.
        Override to use a custom build or a different version.
      '';
    };

    /*
      Future option: variant (not yet implemented).

      variant = lib.mkOption {
        type    = lib.types.enum [ "native" "docker-compose" ];
        default = "native";
        description = ''
          Backend variant for the Temporal dev server.
          - "native": run temporal CLI binary directly (current implementation).
          - "docker-compose": run via Docker Compose (useful for full Temporal stack).
        '';
      };
    */

  };

  # ── Config ──────────────────────────────────────────────────────────────────

  config = lib.mkIf cfg.enable {

    systemd.user.services.temporal-dev-server = {
      Unit = {
        Description     = "Temporal dev server (${cfg.namespace}:${toString cfg.port})";
        Documentation   = "https://docs.temporal.io/cli/server";
        After                 = [ "network.target" ];
        StartLimitBurst       = 5;
        StartLimitIntervalSec = 30;
      };

      Service = lib.mkMerge [
        # Base service config (always applied).
        {
          Restart    = "on-failure";
          RestartSec = 3;

          # Environment hardening for user service.
          Environment = [
            "HOME=%h"
            "PATH=${lib.makeBinPath [ cfg.package pkgs.coreutils ]}"
          ];

          # Graceful shutdown: SIGTERM → 10 s → SIGKILL.
          KillMode          = "process";
          TimeoutStopSec    = 10;
        }

        # When dbPath is set: use it directly, no XDG resolution.
        # Quoting ensures paths with spaces are handled correctly by systemd's
        # ExecStart= argument parser.
        (lib.mkIf (cfg.dbPath != "") {
          ExecStart = lib.concatStringsSep " " (
            [ "${cfg.package}/bin/temporal" ]
            ++ portArgs
            ++ [ "--namespace" (lib.escapeShellArg cfg.namespace) ]
            ++ [ "--db-filename" (lib.escapeShellArg cfg.dbPath) ]
          );
        })

        # When dbPath is empty: resolve XDG path at runtime via wrapper script.
        # The wrapper resolves XDG_DATA_HOME, ensures the db directory exists,
        # then exec's the temporal binary with the resolved path.
        (lib.mkIf (cfg.dbPath == "") {
          ExecStart = "${xdgStartScript}";
        })
      ];

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

  };
}

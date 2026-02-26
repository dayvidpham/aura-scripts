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

  # Build the temporal server start-dev command from options.
  startDevArgs = lib.concatStringsSep " " (
    [ "server" "start-dev" ]
    ++ [ "--port" (toString cfg.port) ]
    ++ [ "--ui-port" (toString cfg.uiPort) ]
    ++ [ "--namespace" cfg.namespace ]
    ++ lib.optionals (cfg.dbPath != "") [ "--db-filename" cfg.dbPath ]
  );

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
        Must match TEMPORAL_NAMESPACE used by bin/worker.py.
      '';
      example     = "aura";
    };

    dbPath = lib.mkOption {
      type        = lib.types.str;
      default     = "";
      description = ''
        Path to SQLite database file for persistence across restarts.
        Empty string (default) uses in-memory storage (data lost on restart).
        Example: "$HOME/.local/share/temporal/temporal.db"
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
        After           = [ "network.target" ];
      };

      Service = {
        ExecStart = "${cfg.package}/bin/temporal ${startDevArgs}";
        Restart   = "on-failure";

        # Environment hardening for user service.
        Environment = [
          "HOME=%h"
          "PATH=${lib.makeBinPath [ cfg.package pkgs.coreutils ]}"
        ];

        # Graceful shutdown: SIGTERM → 10 s → SIGKILL.
        KillMode          = "process";
        TimeoutStopSec    = 10;
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

  };
}

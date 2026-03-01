/*
  aurad-service.nix — home-manager module for the aurad Temporal worker daemon

  Provides a systemd user service running `aurad`. When requireLocalServer
  is true (the default), aurad binds to temporal-dev-server.service: it will
  not start unless temporal is running, and will stop if temporal stops.
  Set requireLocalServer = false when pointing serverAddress at a remote cluster.

  Usage in home.nix:
    imports = [ inputs.aura-plugins.homeManagerModules.aurad-service ];
    services.aurad = {
      enable  = true;
      package = inputs.aura-plugins.packages.${pkgs.system}.aurad;
    };

  Options:
    services.aurad.enable              — whether to enable the service (default: false)
    services.aurad.namespace           — Temporal namespace (default: "default")
    services.aurad.taskQueue           — Temporal task queue (default: "aura")
    services.aurad.serverAddress       — Temporal gRPC address (default: "localhost:7233")
    services.aurad.requireLocalServer  — hard-bind to temporal-dev-server.service (default: true)
    services.aurad.package             — aurad package (required; set to aura-plugins.packages.aurad)
*/

{ self }:

{ config, lib, pkgs, ... }:

let
  cfg       = config.services.aurad;
  systemStr = pkgs.stdenv.hostPlatform.system;
in
{
  # ── Options ─────────────────────────────────────────────────────────────────

  options.services.aurad = {

    enable = lib.mkEnableOption "aurad Temporal worker daemon (systemd user service)";

    namespace = lib.mkOption {
      type        = lib.types.str;
      default     = "default";
      description = "Temporal namespace to connect to.";
      example     = "dev";
    };

    taskQueue = lib.mkOption {
      type        = lib.types.str;
      default     = "aura";
      description = "Temporal task queue name.";
      example     = "aura";
    };

    serverAddress = lib.mkOption {
      type        = lib.types.str;
      default     = "localhost:7233";
      description = "Temporal server gRPC address.";
      example     = "localhost:7233";
    };

    requireLocalServer = lib.mkOption {
      type        = lib.types.bool;
      default     = true;
      description = ''
        Whether aurad requires a co-located temporal-dev-server.service.
        When true (default), aurad uses BindsTo + Requires: it will not start
        unless temporal is running, and will stop if temporal stops.
        Set to false when pointing serverAddress at a remote Temporal cluster.
      '';
    };

    package = lib.mkOption {
      type        = lib.types.package;
      default     = self.packages.${systemStr}.aurad;
      defaultText = lib.literalExpression
        "inputs.aura-plugins.packages.\${pkgs.system}.aurad";
      description = ''
        The aurad package to use. Defaults to the aurad package from this flake.
        Override to pin a specific version or use a custom build.
      '';
    };

  };

  # ── Config ──────────────────────────────────────────────────────────────────

  config = lib.mkIf cfg.enable {

    systemd.user.services.aurad = {
      Unit = lib.mkMerge [
        {
          Description           = "aurad — Aura Protocol Temporal worker daemon";
          Documentation         = "https://github.com/dayvidpham/aura-plugins";
          After                 = [ "network.target" "temporal-dev-server.service" ];
          StartLimitBurst       = 5;
          StartLimitIntervalSec = 30;
        }
        # Hard local dependency: aurad rises and falls with temporal.
        (lib.mkIf cfg.requireLocalServer {
          Requires = [ "temporal-dev-server.service" ];
          BindsTo  = [ "temporal-dev-server.service" ];
        })
        # Soft dependency: best-effort start ordering, no crash propagation.
        (lib.mkIf (!cfg.requireLocalServer) {
          Wants = [ "temporal-dev-server.service" ];
        })
      ];

      Service = {
        ExecStart = lib.concatStringsSep " " [
          "${cfg.package}/bin/aurad"
          "--namespace"      cfg.namespace
          "--task-queue"     cfg.taskQueue
          "--server-address" cfg.serverAddress
        ];

        Restart    = "on-failure";
        RestartSec = 3;

        # Environment hardening for user service.
        Environment = [
          "HOME=%h"
        ];

        # Graceful shutdown: SIGTERM → 10 s → SIGKILL.
        KillMode       = "process";
        TimeoutStopSec = 10;
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

  };
}

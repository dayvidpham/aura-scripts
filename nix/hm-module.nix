{ self }:

{ config
, pkgs
, lib ? config.lib
, ...
}:
let
  cfg = config.CUSTOM.programs.aura-config-sync;

  inherit (lib)
    mkIf
    mkOption
    mkDefault
    mkEnableOption
    mkMerge
    types
    ;

  # ── Source paths within this flake ──
  commandsDir = "${self}/commands";
  protocolDir = "${self}/protocol";
  agentsDir = "${self}/agents";

  # ── Role definitions ──
  # Each role maps to a set of command files with that prefix
  roleNames = [ "architect" "supervisor" "worker" "reviewer" "epoch" ];

  # Collect all .md files in a directory as an attrset: { "filename.md" = storePath; }
  listMdFiles = dir:
    let
      entries = builtins.readDir dir;
      mdFiles = lib.filterAttrs (name: type: type == "regular" && lib.hasSuffix ".md" name) entries;
    in
    lib.mapAttrs (name: _: "${dir}/${name}") mdFiles;

  # Filter command files by role prefix
  allCommandFiles = listMdFiles commandsDir;

  commandsForRole = role:
    lib.filterAttrs
      (name: _: lib.hasPrefix "aura:${role}" name)
      allCommandFiles;

  # Non-role commands (aura:plan, aura:status, aura:test, aura:feedback, aura:msg:*, aura:impl:*, aura:user:*, aura:epoch)
  coreCommands =
    lib.filterAttrs
      (name: _:
        let
          isRoleSpecific = builtins.any (role: lib.hasPrefix "aura:${role}" name) roleNames;
        in
        !isRoleSpecific
      )
      allCommandFiles;

  # Build the set of command files to install based on enabled roles
  enabledCommandFiles =
    let
      roleFiles = builtins.foldl'
        (acc: role:
          if cfg.commands.roles.${role}.enable
          then acc // (commandsForRole role)
          else acc
        )
        { }
        roleNames;
    in
    coreCommands // roleFiles // cfg.commands.extraCommands;

  # ── Agent files ──
  allAgentFiles = listMdFiles agentsDir;

  enabledAgentFiles = allAgentFiles // cfg.agents.extraAgents;

in
{
  options.CUSTOM.programs.aura-config-sync = {
    enable = mkEnableOption "Aura config sync: commands, protocol docs, agents, and settings for Claude Code / OpenCode";

    # ── Packages ──
    packages = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Install launch-parallel and aura-swarm CLI tools";
      };
    };

    # ── Slash commands → ~/.claude/commands/ ──
    commands = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Install Aura slash command .md files into ~/.claude/commands/";
      };

      roles = {
        enableAll = mkOption {
          type = types.bool;
          default = true;
          description = "Enable all agent roles. Set false to pick individual roles.";
        };
      } // (builtins.listToAttrs (map
        (role: {
          name = role;
          value = {
            enable = mkOption {
              type = types.bool;
              default = cfg.commands.roles.enableAll;
              description = "Install ${role} role commands";
            };
          };
        })
        roleNames
      ));

      extraCommands = mkOption {
        type = types.attrsOf types.path;
        default = { };
        description = "Additional command .md files to install. Keys are filenames, values are paths.";
        example = lib.literalExpression ''
          { "my-custom:command.md" = ./my-command.md; }
        '';
      };
    };

    # ── Custom agents → ~/.claude/agents/ ──
    agents = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Install custom agent definitions into ~/.claude/agents/";
      };

      extraAgents = mkOption {
        type = types.attrsOf types.path;
        default = { };
        description = "Additional agent .md files to install.";
      };
    };

    # ── Protocol docs ──
    protocol = {
      enable = mkOption {
        type = types.bool;
        default = false;
        description = "Install protocol docs (CLAUDE.md, CONSTRAINTS.md, PROCESS.md). Disabled by default since projects may have their own CLAUDE.md.";
      };

      target = mkOption {
        type = types.enum [ "global" "xdg" ];
        default = "global";
        description = "Where to install protocol docs. 'global' = ~/.claude/, 'xdg' = ~/.config/aura/protocol/";
      };
    };
  };

  config = mkIf cfg.enable (mkMerge [

    # ── Packages ──
    (mkIf cfg.packages.enable {
      home.packages = [
        self.packages.${pkgs.system}.launch-parallel
        self.packages.${pkgs.system}.aura-swarm
      ];
    })

    # ── Commands ──
    (mkIf cfg.commands.enable {
      home.file = lib.mapAttrs'
        (name: path: {
          name = ".claude/commands/${name}";
          value = { source = path; };
        })
        enabledCommandFiles;
    })

    # ── Agents ──
    (mkIf cfg.agents.enable {
      home.file = lib.mapAttrs'
        (name: path: {
          name = ".claude/agents/${name}";
          value = { source = path; };
        })
        enabledAgentFiles;
    })

    # ── Protocol docs ──
    (mkIf cfg.protocol.enable (
      let
        prefix =
          if cfg.protocol.target == "global"
          then ".claude"
          else ".config/aura/protocol";
        protocolFiles = listMdFiles protocolDir;
      in
      {
        home.file = lib.mapAttrs'
          (name: path: {
            name = "${prefix}/${name}";
            value = { source = path; };
          })
          protocolFiles;
      }
    ))
  ]);
}

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
  skillsDir = "${self}/skills";
  protocolDir = "${self}/skills/protocol";
  agentsDir = "${self}/agents";

  # ── Role definitions ──
  # Each role maps to a set of skill subdirectories with that prefix
  roleNames = [ "architect" "supervisor" "worker" "reviewer" "epoch" ];

  # Collect all .md files in a directory as an attrset: { "filename.md" = storePath; }
  # Used for flat directories (protocol docs, agent files).
  listMdFiles = dir:
    let
      entries = builtins.readDir dir;
      mdFiles = lib.filterAttrs (name: type: type == "regular" && lib.hasSuffix ".md" name) entries;
    in
    lib.mapAttrs (name: _: "${dir}/${name}") mdFiles;

  # Collect all skill subdirectories as an attrset: { "subdir-name" = storePath/SKILL.md; }
  # The new skills/ layout has one subdirectory per skill, each containing a SKILL.md file.
  listSkillFiles = dir:
    let
      entries = builtins.readDir dir;
      subdirs = lib.filterAttrs (name: type: type == "directory") entries;
    in
    lib.filterAttrs (name: path: builtins.pathExists path)
      (lib.mapAttrs (name: _: "${dir}/${name}/SKILL.md") subdirs);

  # Filter skill subdirectories by role prefix
  allSkillFiles = listSkillFiles skillsDir;

  commandsForRole = role:
    lib.filterAttrs
      (name: _: lib.hasPrefix role name)
      allSkillFiles;

  # Non-role skills (plan, status, test, feedback, explore, research, msg-*, impl-*, user-*, etc.)
  coreCommands =
    lib.filterAttrs
      (name: _:
        let
          isRoleSpecific = builtins.any (role: lib.hasPrefix role name) roleNames;
        in
        !isRoleSpecific
      )
      allSkillFiles;

  # Build the set of skill files to install based on enabled roles
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
        description = "Install aura-parallel, aura-swarm, and aura-release CLI tools";
      };
    };

    # ── Plugin skills → ~/skills/ ──
    commands = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Install Aura skill SKILL.md files into ~/skills/";
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
        self.packages.${pkgs.system}.aura-parallel
        self.packages.${pkgs.system}.aura-swarm
        self.packages.${pkgs.system}.aura-release
      ];
    })

    # ── Commands ──
    (mkIf cfg.commands.enable {
      home.file = lib.mapAttrs'
        (name: path: {
          name = "skills/${name}/SKILL.md";
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

"""Regression tests for aura-release version file discovery.

Guards against the bug where discover_version_files() crashed with
FileNotFoundError when run inside a git repo whose root had no pyproject.toml
but a subdirectory did (e.g. agentfilter/opencode-security-filter/).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

# ── Import helper ─────────────────────────────────────────────────────────────

BIN_PATH = Path(__file__).resolve().parent.parent / "bin"

# aura-release has a hyphenated name (no .py extension).
# spec_from_file_location() returns None for extensionless files because Python
# determines the loader from the file extension. SourceFileLoader bypasses this.
# NOTE: this import requires the dead-code block (lines 32-57 in the original)
# to already be removed. With those lines present, import triggers
# REPO_ROOT = _discover_repo_root() at module level, which calls sys.exit(2)
# inside a plain tmp_path (not a git repo).
#
# The module must be registered in sys.modules before exec_module() because
# aura-release uses `from __future__ import annotations` which makes all
# annotations lazy strings. @dataclass resolves these strings by looking up
# sys.modules[cls.__module__].__dict__ — if the module isn't registered,
# this returns None and raises AttributeError.


# ── Fixtures ──────────────────────────────────────────────────────────────────

_VALID_PYPROJECT = '[project]\nname = "pkg"\nversion = "1.0.0"\n'
_TOOL_ONLY_PYPROJECT = "[tool.foo]\nbar = 'baz'\n"  # no [project] section


@pytest.fixture(scope="module")
def aura_release_mod():
    """Import aura-release once per module. Cleans sys.modules at module teardown."""
    loader = SourceFileLoader("aura_release", str(BIN_PATH / "aura-release"))
    spec = importlib.util.spec_from_loader("aura_release", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["aura_release"] = mod  # must register before exec (circular-import safety)
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop("aura_release", None)


@pytest.fixture(autouse=True)
def _clear_caches(aura_release_mod):
    """Clear lru_cache on repo_root between tests (prevents cwd leakage)."""
    yield
    aura_release_mod.repo_root.cache_clear()


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestDiscoverVersionFiles:
    """discover_version_files() driven by _SCAN_SPECS.

    Covers pyproject.toml discovery only (package.json / plugin.json /
    marketplace.json are out of scope for this class — see TestVersionFileWrites).
    Root and subdirectory paths are exercised; version-key filter is verified
    at both levels.
    """

    def test_case_a_root_pyproject(self, tmp_path: Path, aura_release_mod) -> None:
        """Root-level pyproject.toml is discovered (existing happy path)."""
        (tmp_path / "pyproject.toml").write_text(_VALID_PYPROJECT)

        results = aura_release_mod.discover_version_files(tmp_path)

        assert len(results) == 1
        assert results[0].path == tmp_path / "pyproject.toml"

    def test_case_b_subdir_only(self, tmp_path: Path, aura_release_mod) -> None:
        """Subdirectory-only pyproject.toml is discovered (the original bug scenario).

        Previously, the installed binary defined VERSION_FILES["pyproject"] =
        REPO_ROOT / "pyproject.toml" and read it unconditionally, crashing with
        FileNotFoundError when the git root had no pyproject.toml.
        """
        sub = tmp_path / "opencode-security-filter"
        sub.mkdir()
        (sub / "pyproject.toml").write_text(_VALID_PYPROJECT)

        results = aura_release_mod.discover_version_files(tmp_path)

        assert len(results) == 1
        assert results[0].path == sub / "pyproject.toml"

    def test_case_c_both_root_and_subdir(self, tmp_path: Path, aura_release_mod) -> None:
        """Both root and subdirectory pyproject.toml returned, root first.

        Guards against a future short-circuit where only the first match is returned.
        Scan order is structurally guaranteed: root is appended before the
        _subdirs() loop, so root-first is an invariant of discover_version_files().
        """
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "root"\nversion = "2.0.0"\n'
        )
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "pyproject.toml").write_text(
            '[project]\nname = "sub"\nversion = "1.0.0"\n'
        )

        results = aura_release_mod.discover_version_files(tmp_path)

        assert len(results) == 2
        assert results[0].path == tmp_path / "pyproject.toml"
        assert results[1].path == sub / "pyproject.toml"

    def test_case_d_subdir_pyproject_without_version_key(
        self, tmp_path: Path, aura_release_mod
    ) -> None:
        """Subdirectory pyproject.toml without [project] version is excluded.

        Guards against the _has_pyproject_version() filter being accidentally removed.
        A TOML file with only a [tool.*] section has no semver to bump, so it
        must not appear in the discovery results.
        """
        sub = tmp_path / "tool-only"
        sub.mkdir()
        (sub / "pyproject.toml").write_text(_TOOL_ONLY_PYPROJECT)

        results = aura_release_mod.discover_version_files(tmp_path)

        assert results == []

    def test_case_e_root_pyproject_without_version_key(
        self, tmp_path: Path, aura_release_mod
    ) -> None:
        """Root-level pyproject.toml with only [tool.*] section is excluded.

        Guards the _has_pyproject_version() filter at root level (lines 264-266),
        which is distinct from the subdir path tested in test_case_d.
        """
        (tmp_path / "pyproject.toml").write_text(_TOOL_ONLY_PYPROJECT)
        results = aura_release_mod.discover_version_files(tmp_path)
        assert results == []


class TestVersionFileWrites:
    """MarketplaceVersionFile.write() only updates metadata.version, not plugins[*].version."""

    def test_marketplace_write_updates_only_metadata_version(
        self, tmp_path: Path, aura_release_mod
    ) -> None:
        """write() bumps metadata.version but leaves plugins[*].version unchanged."""
        market_path = tmp_path / "marketplace.json"
        market_path.write_text(
            json.dumps(
                {
                    "metadata": {"version": "1.0.0"},
                    "plugins": [{"id": "test-plugin", "version": "1.0.0"}],
                },
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        vf = aura_release_mod.MarketplaceVersionFile(
            name="marketplace.json", path=market_path
        )
        vf.write("1.0.1")

        data = json.loads(market_path.read_text(encoding="utf-8"))
        assert data["metadata"]["version"] == "1.0.1"
        assert data["plugins"][0]["version"] == "1.0.0"  # unchanged

    def test_marketplace_write_dry_run_does_not_write(
        self, tmp_path: Path, aura_release_mod
    ) -> None:
        """write(dry_run=True) does not modify the file on disk."""
        market_path = tmp_path / "marketplace.json"
        original = json.dumps(
            {
                "metadata": {"version": "1.0.0"},
                "plugins": [{"id": "test-plugin", "version": "1.0.0"}],
            },
            indent=2,
        ) + "\n"
        market_path.write_text(original, encoding="utf-8")
        vf = aura_release_mod.MarketplaceVersionFile(
            name="marketplace.json", path=market_path
        )
        vf.write("1.0.1", dry_run=True)

        data = json.loads(market_path.read_text(encoding="utf-8"))
        assert data["metadata"]["version"] == "1.0.0"  # unchanged


class TestPluginRegistry:
    """PluginRegistry.load() and find_plugin() behavior."""

    def test_load_returns_none_if_absent(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """load() returns None when the registry file does not exist."""
        monkeypatch.setattr(
            aura_release_mod, "_registry_path", lambda: tmp_path / "nonexistent.json"
        )
        assert aura_release_mod.PluginRegistry.load() is None

    def test_load_exits_on_malformed_json(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """load() calls sys.exit(2) when registry file contains invalid JSON."""
        reg = tmp_path / "registry.json"
        reg.write_text("not json")
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg)
        with pytest.raises(SystemExit) as exc:
            aura_release_mod.PluginRegistry.load()
        assert exc.value.code == 2

    def test_load_exits_on_missing_marketplaces_key(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """load() calls sys.exit(2) when registry JSON lacks 'marketplaces' key."""
        reg = tmp_path / "registry.json"
        reg.write_text(json.dumps({"version": 1}))
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg)
        with pytest.raises(SystemExit) as exc:
            aura_release_mod.PluginRegistry.load()
        assert exc.value.code == 2

    def test_load_warns_and_skips_nonexistent_marketplace(
        self, tmp_path: Path, aura_release_mod, monkeypatch, capsys
    ) -> None:
        """load() warns to stderr and skips a marketplace whose path does not exist."""
        reg = tmp_path / "registry.json"
        reg.write_text(json.dumps({
            "marketplaces": [
                {"path": str(tmp_path / "no-such-dir"), "plugins": []}
            ]
        }))
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg)
        result = aura_release_mod.PluginRegistry.load()
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert result is not None
        assert len(result.marketplaces) == 0

    def test_load_warns_and_skips_malformed_plugin_entry(
        self, tmp_path: Path, aura_release_mod, monkeypatch, capsys
    ) -> None:
        """load() warns to stderr and skips plugin entries missing name or path."""
        mp_dir = tmp_path / "market"
        mp_dir.mkdir()
        reg = tmp_path / "registry.json"
        reg.write_text(json.dumps({
            "marketplaces": [
                {
                    "path": str(mp_dir),
                    "plugins": [{"version": "1.0.0"}],  # missing name and path
                }
            ]
        }))
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg)
        result = aura_release_mod.PluginRegistry.load()
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert result is not None
        assert len(result.marketplaces) == 1
        assert len(result.marketplaces[0].plugins) == 0

    def test_find_plugin_by_name(self, tmp_path: Path, aura_release_mod) -> None:
        """find_plugin() returns (PluginEntry, MarketplaceEntry) when name matches."""
        plugin_path = tmp_path / "my-plugin"
        plugin_path.mkdir()
        entry = aura_release_mod.PluginEntry(
            name="my-plugin",
            path=plugin_path,
            remote=None,
        )
        marketplace = aura_release_mod.MarketplaceEntry(
            path=tmp_path / "marketplace.json",
            plugins=(entry,),
        )
        registry = aura_release_mod.PluginRegistry(marketplaces=(marketplace,))
        result = registry.find_plugin("my-plugin", tmp_path)
        assert result is not None
        found_plugin, found_market = result
        assert found_plugin.name == "my-plugin"
        assert found_market is marketplace

    def test_find_plugin_by_cwd_auto_detect(
        self, tmp_path: Path, aura_release_mod
    ) -> None:
        """find_plugin(name=None) auto-detects plugin by resolved cwd path."""
        plugin_path = tmp_path / "my-plugin"
        plugin_path.mkdir()
        entry = aura_release_mod.PluginEntry(
            name="my-plugin",
            path=plugin_path.resolve(),
            remote=None,
        )
        marketplace = aura_release_mod.MarketplaceEntry(
            path=tmp_path / "marketplace.json",
            plugins=(entry,),
        )
        registry = aura_release_mod.PluginRegistry(marketplaces=(marketplace,))
        result = registry.find_plugin(None, plugin_path)
        assert result is not None
        found_plugin, _ = result
        assert found_plugin.name == "my-plugin"

    def test_find_plugin_returns_none_when_no_match(
        self, tmp_path: Path, aura_release_mod
    ) -> None:
        """find_plugin() returns None when no entry matches name or cwd."""
        registry = aura_release_mod.PluginRegistry(marketplaces=())
        assert registry.find_plugin("nonexistent", tmp_path) is None


class TestRegistryCLI:
    """cmd_registry_init/add/list/remove via cmd_registry dispatch."""

    def test_registry_init_creates_empty_registry(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """init creates a registry file with {'marketplaces': []}."""
        reg_path = tmp_path / "registry.json"
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)

        rc = aura_release_mod.cmd_registry(["init"])

        assert rc == 0
        assert reg_path.exists()
        data = json.loads(reg_path.read_text(encoding="utf-8"))
        assert data == {"marketplaces": []}

    def test_registry_init_errors_if_already_exists(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """init exits with code 1 when the registry file already exists."""
        reg_path = tmp_path / "registry.json"
        reg_path.write_text(json.dumps({"marketplaces": []}))
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)

        rc = aura_release_mod.cmd_registry(["init"])

        assert rc == 1

    def test_registry_add_creates_entry(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """add creates a plugin entry under the given marketplace path."""
        reg_path = tmp_path / "registry.json"
        reg_path.write_text(json.dumps({"marketplaces": []}) + "\n")
        mp_path = tmp_path / "marketplace.json"
        mp_path.write_text(json.dumps({"metadata": {"version": "1.0.0"}}))
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)

        rc = aura_release_mod.cmd_registry([
            "add", "my-plugin",
            "--path", str(plugin_dir),
            "--marketplace", str(mp_path),
        ])

        assert rc == 0
        data = json.loads(reg_path.read_text(encoding="utf-8"))
        assert len(data["marketplaces"]) == 1
        plugins = data["marketplaces"][0]["plugins"]
        assert len(plugins) == 1
        assert plugins[0]["name"] == "my-plugin"

    def test_registry_add_stores_path_as_absolute(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """add stores the plugin path as an absolute path (Path.resolve() at add time)."""
        reg_path = tmp_path / "registry.json"
        reg_path.write_text(json.dumps({"marketplaces": []}) + "\n")
        mp_path = tmp_path / "marketplace.json"
        mp_path.write_text(json.dumps({"metadata": {"version": "1.0.0"}}))
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)

        rc = aura_release_mod.cmd_registry([
            "add", "my-plugin",
            "--path", str(plugin_dir),
            "--marketplace", str(mp_path),
        ])

        assert rc == 0
        data = json.loads(reg_path.read_text(encoding="utf-8"))
        stored_path = data["marketplaces"][0]["plugins"][0]["path"]
        assert Path(stored_path).is_absolute()
        assert Path(stored_path) == plugin_dir.resolve()

    def test_registry_add_duplicate_prompts_confirm(
        self, tmp_path: Path, aura_release_mod, monkeypatch, capsys
    ) -> None:
        """add on duplicate name prints old entry and prompts 'Update? [y/N]'."""
        reg_path = tmp_path / "registry.json"
        mp_path = tmp_path / "marketplace.json"
        mp_path.write_text(json.dumps({"metadata": {"version": "1.0.0"}}))
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        # Pre-populate registry with an existing entry
        initial_data = {
            "marketplaces": [
                {
                    "path": str(mp_path),
                    "plugins": [
                        {"name": "my-plugin", "path": str(plugin_dir), "remote": None}
                    ],
                }
            ]
        }
        reg_path.write_text(json.dumps(initial_data) + "\n")
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)
        # Simulate user answering "n" to abort
        monkeypatch.setattr("builtins.input", lambda _: "n")

        rc = aura_release_mod.cmd_registry([
            "add", "my-plugin",
            "--path", str(plugin_dir),
            "--marketplace", str(mp_path),
        ])

        assert rc == 0
        captured = capsys.readouterr()
        assert "Existing entry" in captured.out
        assert "Update? [y/N]" in captured.out

    def test_registry_add_duplicate_with_yes_flag_skips_prompt(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """add --yes skips the 'Update? [y/N]' prompt on duplicate."""
        reg_path = tmp_path / "registry.json"
        mp_path = tmp_path / "marketplace.json"
        mp_path.write_text(json.dumps({"metadata": {"version": "1.0.0"}}))
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        new_plugin_dir = tmp_path / "my-plugin-v2"
        new_plugin_dir.mkdir()
        initial_data = {
            "marketplaces": [
                {
                    "path": str(mp_path),
                    "plugins": [
                        {"name": "my-plugin", "path": str(plugin_dir), "remote": None}
                    ],
                }
            ]
        }
        reg_path.write_text(json.dumps(initial_data) + "\n")
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)
        # Ensure input() is never called (would raise if prompt appeared)
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(AssertionError("input() must not be called with --yes")))

        rc = aura_release_mod.cmd_registry([
            "add", "my-plugin",
            "--path", str(new_plugin_dir),
            "--marketplace", str(mp_path),
            "--yes",
        ])

        assert rc == 0
        data = json.loads(reg_path.read_text(encoding="utf-8"))
        plugins = data["marketplaces"][0]["plugins"]
        assert len(plugins) == 1
        assert Path(plugins[0]["path"]) == new_plugin_dir.resolve()

    def test_registry_list_output_format(
        self, tmp_path: Path, aura_release_mod, monkeypatch, capsys
    ) -> None:
        """list prints '<marketplace-path> → <name> (<plugin-path>)' per entry."""
        reg_path = tmp_path / "registry.json"
        mp_path = tmp_path / "marketplace.json"
        mp_path.write_text(json.dumps({"metadata": {"version": "1.0.0"}}))
        plugin_dir = (tmp_path / "my-plugin").resolve()
        plugin_dir.mkdir()
        data = {
            "marketplaces": [
                {
                    "path": str(mp_path.resolve()),
                    "plugins": [
                        {"name": "my-plugin", "path": str(plugin_dir), "remote": None}
                    ],
                }
            ]
        }
        reg_path.write_text(json.dumps(data) + "\n")
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)

        rc = aura_release_mod.cmd_registry(["list"])

        assert rc == 0
        captured = capsys.readouterr()
        assert f"{mp_path.resolve()} → my-plugin ({plugin_dir})" in captured.out

    def test_registry_remove_by_name(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """remove deletes all plugin entries matching the given name."""
        reg_path = tmp_path / "registry.json"
        mp_path = tmp_path / "marketplace.json"
        mp_path.write_text(json.dumps({"metadata": {"version": "1.0.0"}}))
        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        data = {
            "marketplaces": [
                {
                    "path": str(mp_path.resolve()),
                    "plugins": [
                        {"name": "my-plugin", "path": str(plugin_dir.resolve()), "remote": None}
                    ],
                }
            ]
        }
        reg_path.write_text(json.dumps(data) + "\n")
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)

        rc = aura_release_mod.cmd_registry(["remove", "my-plugin"])

        assert rc == 0
        saved = json.loads(reg_path.read_text(encoding="utf-8"))
        plugins = saved["marketplaces"][0]["plugins"]
        assert all(p["name"] != "my-plugin" for p in plugins)

    def test_registry_remove_noop_if_absent(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """remove is a no-op (exit 0) when the plugin name is not in the registry."""
        reg_path = tmp_path / "registry.json"
        mp_path = tmp_path / "marketplace.json"
        mp_path.write_text(json.dumps({"metadata": {"version": "1.0.0"}}))
        data = {
            "marketplaces": [
                {
                    "path": str(mp_path.resolve()),
                    "plugins": [],
                }
            ]
        }
        reg_path.write_text(json.dumps(data) + "\n")
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)

        rc = aura_release_mod.cmd_registry(["remove", "nonexistent"])

        assert rc == 0


# ── Release integration tests ─────────────────────────────────────────────────


def _make_plugin_dir(tmp_path: Path, *, plugin_name: str = "my-plugin") -> Path:
    """Create a minimal plugin directory with a pyproject.toml version file."""
    plugin_dir = tmp_path / plugin_name
    plugin_dir.mkdir()
    (plugin_dir / "pyproject.toml").write_text(
        '[project]\nname = "my-plugin"\nversion = "1.0.0"\n'
    )
    return plugin_dir


def _make_marketplace(tmp_path: Path) -> Path:
    """Create a minimal marketplace.json file."""
    mp_path = tmp_path / "marketplace.json"
    mp_path.write_text(
        json.dumps({"metadata": {"version": "1.0.0"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    return mp_path


def _make_registry(
    tmp_path: Path,
    *,
    plugin_dir: Path,
    marketplace_path: Path,
    plugin_name: str = "my-plugin",
) -> Path:
    """Write a registry JSON pointing to the given plugin/marketplace."""
    reg_path = tmp_path / "registry.json"
    data = {
        "marketplaces": [
            {
                "path": str(marketplace_path.resolve()),
                "plugins": [
                    {
                        "name": plugin_name,
                        "path": str(plugin_dir.resolve()),
                        "remote": None,
                    }
                ],
            }
        ]
    }
    reg_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return reg_path


def _patch_release_deps(monkeypatch, aura_release_mod, *, root: Path) -> None:
    """Monkeypatch all git-touching functions in cmd_release() for integration tests."""
    monkeypatch.setattr(aura_release_mod, "repo_root", lambda: root)
    monkeypatch.setattr(aura_release_mod, "is_detached_head", lambda: False)
    monkeypatch.setattr(aura_release_mod, "working_tree_dirty", lambda: False)
    monkeypatch.setattr(aura_release_mod, "latest_version_tag", lambda: None)
    monkeypatch.setattr(aura_release_mod, "all_commits", lambda: [])
    monkeypatch.setattr(aura_release_mod, "git", lambda *a, **kw: None)


def _make_args(aura_release_mod, **kwargs):
    """Build a minimal Namespace for cmd_release() / cmd_check()."""
    import argparse
    defaults = dict(
        bump="patch",
        dry_run=False,
        sync=False,
        no_changelog=True,
        no_commit=True,
        no_tag=True,
        plugin=None,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestReleaseRegistryIntegration:
    """Integration tests for registry lookup wired into cmd_release() and cmd_check()."""

    def test_release_dry_run_skips_registry_write(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """--dry-run prints [dry-run] message and does NOT write marketplace.json."""
        plugin_dir = _make_plugin_dir(tmp_path)
        marketplace_path = _make_marketplace(tmp_path)
        # Marketplace is separate from the plugin dir, so it won't be in discovered_paths
        reg_path = _make_registry(
            tmp_path,
            plugin_dir=plugin_dir,
            marketplace_path=marketplace_path,
        )
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)
        _patch_release_deps(monkeypatch, aura_release_mod, root=plugin_dir)

        original_content = marketplace_path.read_text(encoding="utf-8")
        args = _make_args(aura_release_mod, dry_run=True, plugin="my-plugin")
        rc = aura_release_mod.cmd_release(args)

        assert rc == 0
        # Marketplace file must NOT be modified during dry-run
        assert marketplace_path.read_text(encoding="utf-8") == original_content

    def test_release_errors_verbosely_when_registry_exists_no_match(
        self, tmp_path: Path, aura_release_mod, monkeypatch, capsys
    ) -> None:
        """Registry present but no matching plugin → error to stderr + return 1."""
        plugin_dir = _make_plugin_dir(tmp_path)
        marketplace_path = _make_marketplace(tmp_path)
        # Registry contains "other-plugin", but we ask for "my-plugin" (no match by name)
        other_dir = tmp_path / "other-plugin"
        other_dir.mkdir()
        reg_path = _make_registry(
            tmp_path,
            plugin_dir=other_dir,
            marketplace_path=marketplace_path,
            plugin_name="other-plugin",
        )
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)
        # Root is plugin_dir, which does NOT match other_dir
        _patch_release_deps(monkeypatch, aura_release_mod, root=plugin_dir)

        # No --plugin flag → auto-detect by cwd (plugin_dir != other_dir → no match)
        args = _make_args(aura_release_mod, plugin=None)
        rc = aura_release_mod.cmd_release(args)

        captured = capsys.readouterr()
        assert rc == 1
        assert "plugin registry found but no match" in captured.err
        assert "--plugin" in captured.err

    def test_check_shows_registry_info_when_found(
        self, tmp_path: Path, aura_release_mod, monkeypatch, capsys
    ) -> None:
        """--check prints 'Registry: plugin=<name> marketplace=<path>' when matched."""
        plugin_dir = _make_plugin_dir(tmp_path)
        marketplace_path = _make_marketplace(tmp_path)
        reg_path = _make_registry(
            tmp_path,
            plugin_dir=plugin_dir,
            marketplace_path=marketplace_path,
        )
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)
        monkeypatch.setattr(aura_release_mod, "repo_root", lambda: plugin_dir)

        args = _make_args(aura_release_mod, plugin=None)
        rc = aura_release_mod.cmd_check(args)

        captured = capsys.readouterr()
        assert rc == 0
        assert f"Registry: plugin=my-plugin marketplace={marketplace_path.resolve()}" in captured.out

    def test_double_bump_guard_prevents_duplicate_write(
        self, tmp_path: Path, aura_release_mod, monkeypatch
    ) -> None:
        """When marketplace.json is already in discovered_paths, do NOT write it again."""
        plugin_dir = _make_plugin_dir(tmp_path)
        # Put marketplace.json inside .claude-plugin/ so discover_version_files() finds it
        claude_plugin_dir = plugin_dir / ".claude-plugin"
        claude_plugin_dir.mkdir()
        marketplace_path = claude_plugin_dir / "marketplace.json"
        marketplace_path.write_text(
            json.dumps({"metadata": {"version": "1.0.0"}}, indent=2) + "\n",
            encoding="utf-8",
        )

        reg_path = _make_registry(
            tmp_path,
            plugin_dir=plugin_dir,
            marketplace_path=marketplace_path,
        )
        monkeypatch.setattr(aura_release_mod, "_registry_path", lambda: reg_path)
        _patch_release_deps(monkeypatch, aura_release_mod, root=plugin_dir)

        args = _make_args(aura_release_mod, dry_run=False, plugin="my-plugin")
        rc = aura_release_mod.cmd_release(args)

        assert rc == 0
        # metadata.version was bumped by the main version-file loop (1.0.0 -> 1.0.1)
        # The registry code must NOT bump it a second time (guard by resolved_mp not in discovered_paths)
        data = json.loads(marketplace_path.read_text(encoding="utf-8"))
        assert data["metadata"]["version"] == "1.0.1"  # bumped exactly once

#!/usr/bin/env python3
"""
cursor_sandbox_doctor.py

Diagnose and repair the common Cursor terminal sandbox failure on Ubuntu 24.04 / Linux Mint 22
caused by incomplete or stale AppArmor configuration.

What it does:
- Collects local diagnostics (kernel, AppArmor, Cursor profile files, Cursor logs).
- Detects likely failure modes: unix socket/network, netlink/loopback, user namespace, stale profile.
- Backs up any file it touches.
- Patches /etc/apparmor.d/cursor-sandbox safely.
- Creates /etc/apparmor.d/cursor-system when user namespace restrictions are implicated.
- Ensures the Cursor sandbox helper binary has the expected setuid bit.
- Reloads AppArmor profiles.
- Prints a structured summary with actions taken and anything still uncertain.

Safety principles:
- Only touches Cursor-related AppArmor files and Cursor helper binaries.
- Creates timestamped backups before every change.
- Rolls back a file if apparmor_parser rejects the new profile.
- Does NOT disable AppArmor globally.
- Does NOT kill or restart Cursor automatically.

Usage:
    sudo python3 cursor_sandbox_doctor.py
    sudo python3 cursor_sandbox_doctor.py --diagnose-only
    sudo python3 cursor_sandbox_doctor.py --verbose
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


CURSOR_PROFILE_CANDIDATES = [
    Path("/etc/apparmor.d/cursor-sandbox"),
    Path("/etc/apparmor.d/cursor_sandbox"),
]
CURSOR_SYSTEM_PROFILE = Path("/etc/apparmor.d/cursor-system")
CURSOR_REMOTE_PROFILE = Path("/etc/apparmor.d/cursor-sandbox-remote")

CURSOR_EXECUTABLE_CANDIDATES = [
    Path("/usr/share/cursor/cursor"),
    Path("/opt/Cursor/cursor"),
]

CURSOR_HELPER_CANDIDATES = [
    Path("/usr/share/cursor/resources/app/resources/helpers/cursorsandbox"),
    Path("/usr/share/cursor/resources/app/resources/helpers/cursor-sandbox"),
    Path("/opt/Cursor/resources/app/resources/helpers/cursorsandbox"),
    Path("/opt/Cursor/resources/app/resources/helpers/cursor-sandbox"),
]

CURSOR_LOG_DIRS = [
    Path.home() / ".config/Cursor/logs",
    Path.home() / ".config/cursor/logs",
]

DEFAULT_BACKUP_ROOT = Path("/var/backups/cursor_sandbox_doctor")


@dataclass
class CmdResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class Findings:
    apparmor_enabled: Optional[bool] = None
    aa_status_available: bool = False
    apparmor_parser_available: bool = False
    userns_restricted: Optional[bool] = None
    kernel: str = ""
    distro: str = ""
    local_profile: Optional[Path] = None
    stale_profile: Optional[Path] = None
    helper_path: Optional[Path] = None
    helper_needs_setuid: bool = False
    cursor_executable: Optional[Path] = None
    loaded_profiles: List[str] = field(default_factory=list)
    log_hits: List[str] = field(default_factory=list)
    failure_modes: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class CursorSandboxDoctor:
    def __init__(self, diagnose_only: bool = False, verbose: bool = False) -> None:
        self.diagnose_only = diagnose_only
        self.verbose = verbose
        self.findings = Findings()
        self.actions: List[str] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.backup_root = DEFAULT_BACKUP_ROOT / self.timestamp

    def log(self, msg: str) -> None:
        print(msg)

    def debug(self, msg: str) -> None:
        if self.verbose:
            print(f"[debug] {msg}")

    def run(self, cmd: List[str], check: bool = False, capture: bool = True) -> CmdResult:
        self.debug(f"Running: {' '.join(cmd)}")
        completed = subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=capture,
        )
        result = CmdResult(completed.returncode, completed.stdout if capture else "", completed.stderr if capture else "")
        if check and not result.ok:
            raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}\n{result.stderr or result.stdout}")
        return result

    def ensure_root(self) -> None:
        if os.geteuid() == 0:
            return
        if self.diagnose_only:
            self.warnings.append("Not running as root. Diagnosis can continue, but repairs/reloads will be skipped.")
            return
        if shutil.which("sudo") is None:
            raise SystemExit("This script must run as root for repair mode, and sudo is not available.")
        self.log("Re-running with sudo...")
        os.execvp("sudo", ["sudo", sys.executable, *sys.argv])

    def backup_file(self, path: Path) -> Path:
        self.backup_root.mkdir(parents=True, exist_ok=True)
        relative = path.as_posix().lstrip("/")
        destination = self.backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        self.debug(f"Backup created: {destination}")
        return destination

    def write_text_atomic(self, path: Path, content: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)

    def detect_environment(self) -> None:
        self.findings.kernel = platform.release()
        self.findings.distro = self._read_os_release()
        self.findings.apparmor_enabled = self._read_apparmor_enabled()
        self.findings.aa_status_available = shutil.which("aa-status") is not None
        self.findings.apparmor_parser_available = shutil.which("apparmor_parser") is not None
        self.findings.userns_restricted = self._read_userns_restriction()

        for path in CURSOR_PROFILE_CANDIDATES:
            if path.exists():
                if path.name == "cursor-sandbox" and self.findings.local_profile is None:
                    self.findings.local_profile = path
                elif path.name == "cursor_sandbox":
                    self.findings.stale_profile = path
                    if self.findings.local_profile is None:
                        self.findings.local_profile = path

        for exe in CURSOR_EXECUTABLE_CANDIDATES:
            if exe.exists():
                self.findings.cursor_executable = exe
                break

        for helper in CURSOR_HELPER_CANDIDATES:
            if helper.exists():
                self.findings.helper_path = helper
                mode = helper.stat().st_mode
                self.findings.helper_needs_setuid = not bool(mode & stat.S_ISUID)
                break

        if self.findings.aa_status_available:
            result = self.run(["aa-status"])
            if result.ok:
                self.findings.loaded_profiles = [
                    line.strip() for line in result.stdout.splitlines()
                    if "cursor" in line.lower()
                ]

    def _read_os_release(self) -> str:
        os_release = Path("/etc/os-release")
        if not os_release.exists():
            return platform.platform()
        data = {}
        for line in os_release.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                data[k] = v.strip().strip('"')
        pretty = data.get("PRETTY_NAME")
        return pretty or platform.platform()

    def _read_apparmor_enabled(self) -> Optional[bool]:
        enabled_path = Path("/sys/module/apparmor/parameters/enabled")
        if not enabled_path.exists():
            return None
        raw = enabled_path.read_text(encoding="utf-8", errors="ignore").strip().upper()
        if raw.startswith("Y"):
            return True
        if raw.startswith("N"):
            return False
        return None

    def _read_userns_restriction(self) -> Optional[bool]:
        if shutil.which("sysctl") is None:
            return None
        result = self.run(["sysctl", "-n", "kernel.apparmor_restrict_unprivileged_userns"])
        if not result.ok:
            return None
        value = result.stdout.strip()
        if value == "1":
            return True
        if value == "0":
            return False
        return None

    def scan_logs(self) -> None:
        patterns = [
            (re.compile(r"Failed to apply sandbox", re.I), "sandbox failure"),
            (re.compile(r"user namespace|uid_map|CLONE_NEWUSER|unshare namespaces|Operation not permitted", re.I), "userns"),
            (re.compile(r"loopback|NETLINK_ROUTE|netlink", re.I), "loopback/netlink"),
            (re.compile(r"unix", re.I), "unix/network"),
            (re.compile(r"EPERM", re.I), "permission"),
        ]
        seen = set()

        for log_dir in CURSOR_LOG_DIRS:
            if not log_dir.exists():
                continue
            files = sorted(
                [p for p in log_dir.rglob("*.log") if p.is_file()],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:20]
            for file in files:
                try:
                    text = file.read_text(encoding="utf-8", errors="ignore")[-200_000:]
                except Exception:
                    continue
                if "sandbox" not in text.lower() and "apparmor" not in text.lower():
                    continue
                for regex, label in patterns:
                    if regex.search(text):
                        hit = f"{file}: {label}"
                        if hit not in seen:
                            self.findings.log_hits.append(hit)
                            seen.add(hit)

                lower = text.lower()
                if any(k in lower for k in ["uid_map", "user namespace", "clone_newuser", "unshare namespaces"]):
                    self._add_failure_mode("userns")
                if any(k in lower for k in ["loopback", "netlink_route", "netlink"]):
                    self._add_failure_mode("loopback/netlink")
                if "network unix" in lower or ("unix" in lower and "socket" in lower):
                    self._add_failure_mode("unix/network")

        if os.geteuid() == 0 and shutil.which("journalctl"):
            result = self.run([
                "journalctl", "-k", "-b", "--no-pager",
                "--grep", r"apparmor=\"DENIED\"|cursor|unprivileged_userns"
            ])
            if result.ok:
                text = result.stdout[-100_000:]
                lower = text.lower()
                if "uid_map" in lower or "userns" in lower or "unprivileged_userns" in lower:
                    self._add_failure_mode("userns")
                if "netlink" in lower or "loopback" in lower:
                    self._add_failure_mode("loopback/netlink")
                if "unix" in lower:
                    self._add_failure_mode("unix/network")

        # Heuristic fallback for the known local desktop issue.
        if self.findings.local_profile and "userns" not in self.findings.failure_modes and "loopback/netlink" not in self.findings.failure_modes:
            self._add_failure_mode("unix/network")

    def _add_failure_mode(self, mode: str) -> None:
        if mode not in self.findings.failure_modes:
            self.findings.failure_modes.append(mode)

    def patch_local_profile(self) -> None:
        profile = self.findings.local_profile
        if profile is None:
            self.warnings.append("No local Cursor AppArmor profile was found under /etc/apparmor.d.")
            return
        if not profile.exists():
            self.warnings.append(f"Expected local profile not found: {profile}")
            return

        required_rules = []
        if "unix/network" in self.findings.failure_modes:
            required_rules.append("network unix,")
        if "loopback/netlink" in self.findings.failure_modes:
            required_rules.extend([
                "capability net_admin,",
                "network,",
            ])
        if "userns" in self.findings.failure_modes:
            required_rules.append("userns,")

        required_rules = self._dedupe_keep_order(required_rules)
        if not required_rules:
            self.findings.notes.append("No local profile rules needed patching.")
            return

        original = profile.read_text(encoding="utf-8", errors="ignore")
        updated = self._ensure_profile_preamble(original)
        updated = self._ensure_rules_in_profile_blocks(updated, required_rules)

        if updated == original:
            self.findings.notes.append(f"No content change needed in {profile}.")
            return

        backup = self.backup_file(profile)
        self.write_text_atomic(profile, updated)
        if not self._reload_profile(profile):
            shutil.copy2(backup, profile)
            self.errors.append(f"Reload failed after editing {profile}. Restored backup from {backup}.")
            return

        self.actions.append(f"Patched and reloaded local profile: {profile}")

    def create_or_update_cursor_system_profile(self) -> None:
        if self.findings.cursor_executable is None:
            self.warnings.append("Cursor executable not found under expected paths; skipping cursor-system profile creation.")
            return

        need_system_profile = (
            "userns" in self.findings.failure_modes
            or self.findings.userns_restricted is True
        )
        if not need_system_profile:
            return

        desired = (
            "abi <abi/4.0>,\n"
            "include <tunables/global>\n\n"
            f'profile cursor-system "{self.findings.cursor_executable}" flags=(unconfined) {{\n'
            "  userns,\n"
            "  include if exists <local/cursor>\n"
            "}\n"
        )

        original = CURSOR_SYSTEM_PROFILE.read_text(encoding="utf-8", errors="ignore") if CURSOR_SYSTEM_PROFILE.exists() else None
        if original == desired:
            if self._reload_profile(CURSOR_SYSTEM_PROFILE):
                self.findings.notes.append("cursor-system profile already matched the desired content.")
            return

        if CURSOR_SYSTEM_PROFILE.exists():
            backup = self.backup_file(CURSOR_SYSTEM_PROFILE)
        else:
            backup = None
            CURSOR_SYSTEM_PROFILE.parent.mkdir(parents=True, exist_ok=True)

        self.write_text_atomic(CURSOR_SYSTEM_PROFILE, desired)
        if not self._reload_profile(CURSOR_SYSTEM_PROFILE):
            if backup and backup.exists():
                shutil.copy2(backup, CURSOR_SYSTEM_PROFILE)
            else:
                CURSOR_SYSTEM_PROFILE.unlink(missing_ok=True)
            self.errors.append("Reload failed after writing /etc/apparmor.d/cursor-system. Rolled back.")
            return

        self.actions.append(f"Installed/reloaded cursor-system profile: {CURSOR_SYSTEM_PROFILE}")

    def disable_stale_profile_if_needed(self) -> None:
        stale = self.findings.stale_profile
        local = self.findings.local_profile
        if stale is None or not stale.exists():
            return
        if local is None or stale == local:
            return

        disabled = stale.with_name(f"{stale.name}.disabled")
        if disabled.exists():
            self.findings.notes.append(f"Stale profile already disabled: {disabled}")
            return

        if not self.diagnose_only and os.geteuid() == 0 and self.findings.apparmor_parser_available:
            self.run(["apparmor_parser", "-R", str(stale)])

        backup = self.backup_file(stale)
        stale.rename(disabled)
        self.actions.append(f"Disabled stale profile {stale} -> {disabled} (backup: {backup})")

    def ensure_helper_permissions(self) -> None:
        helper = self.findings.helper_path
        if helper is None or not helper.exists():
            self.warnings.append("Cursor sandbox helper binary was not found in the expected install paths.")
            return
        current_mode = helper.stat().st_mode
        desired_mode = current_mode | stat.S_ISUID
        if current_mode == desired_mode:
            self.findings.notes.append(f"Helper already has setuid bit: {helper}")
            return

        backup = self.backup_file(helper)
        os.chmod(helper, desired_mode)
        self.actions.append(f"Set setuid bit on helper binary: {helper} (backup metadata snapshot: {backup})")

    def _reload_profile(self, profile: Path) -> bool:
        if not self.findings.apparmor_parser_available:
            self.errors.append("apparmor_parser is not available; cannot reload profiles.")
            return False
        result = self.run(["apparmor_parser", "-r", str(profile)])
        if not result.ok:
            self.debug(result.stderr or result.stdout)
            return False
        return True

    def _ensure_profile_preamble(self, text: str) -> str:
        lines = text.splitlines()
        stripped = [line.strip() for line in lines if line.strip()]
        needs_abi = not any(line.startswith("abi <abi/4.0>") for line in stripped)
        needs_tunables = not any(line == "include <tunables/global>" for line in stripped)

        preamble = []
        if needs_abi:
            preamble.append("abi <abi/4.0>,")
        if needs_tunables:
            preamble.append("include <tunables/global>")
        if not preamble:
            return text

        return "\n".join(preamble) + "\n\n" + text.lstrip("\n")

    def _ensure_rules_in_profile_blocks(self, text: str, rules):
        lines = text.splitlines()
        i = 0
        changed = False

        while i < len(lines):
            if re.match(r"^\s*profile\s+.+\{\s*$", lines[i]):
                start = i
                depth = lines[i].count("{") - lines[i].count("}")
                j = i + 1
                while j < len(lines):
                    depth += lines[j].count("{") - lines[j].count("}")
                    if depth <= 0:
                        break
                    j += 1
                if j >= len(lines):
                    break

                block_lines = lines[start:j + 1]
                block_text = "\n".join(block_lines)
                missing = [rule for rule in rules if rule not in block_text]
                if missing:
                    insert_at = j
                    indent = self._infer_indent(block_lines)
                    to_insert = [f"{indent}{rule}" for rule in missing]
                    lines[insert_at:insert_at] = to_insert
                    delta = len(to_insert)
                    j += delta
                    i = j
                    changed = True
                else:
                    i = j
            i += 1

        if not changed:
            return text
        return "\n".join(lines) + ("\n" if text.endswith("\n") else "")

    def _infer_indent(self, block_lines):
        for line in block_lines[1:]:
            stripped = line.strip()
            if stripped and stripped != "}":
                match = re.match(r"^\s*", line)
                return match.group(0) if match else ""
        return "  "

    def _dedupe_keep_order(self, items):
        seen = set()
        out = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    def print_summary(self) -> None:
        summary = {
            "timestamp": self.timestamp,
            "diagnose_only": self.diagnose_only,
            "environment": {
                "distro": self.findings.distro,
                "kernel": self.findings.kernel,
                "apparmor_enabled": self.findings.apparmor_enabled,
                "apparmor_parser_available": self.findings.apparmor_parser_available,
                "aa_status_available": self.findings.aa_status_available,
                "userns_restricted": self.findings.userns_restricted,
            },
            "cursor": {
                "local_profile": str(self.findings.local_profile) if self.findings.local_profile else None,
                "stale_profile": str(self.findings.stale_profile) if self.findings.stale_profile else None,
                "cursor_executable": str(self.findings.cursor_executable) if self.findings.cursor_executable else None,
                "helper_path": str(self.findings.helper_path) if self.findings.helper_path else None,
                "helper_needs_setuid": self.findings.helper_needs_setuid,
            },
            "failure_modes": self.findings.failure_modes,
            "loaded_profiles": self.findings.loaded_profiles,
            "log_hits": self.findings.log_hits[-20:],
            "actions": self.actions,
            "notes": self.findings.notes,
            "warnings": self.warnings,
            "errors": self.errors,
            "backup_root": str(self.backup_root if self.backup_root.exists() else ""),
        }

        print("\n=== Cursor Sandbox Doctor Summary ===")
        print(json.dumps(summary, indent=2, ensure_ascii=False))

        print("\nNext steps:")
        if self.errors:
            print("- The script found an error while applying a change. Review the summary and restore from backup if needed.")
        elif self.diagnose_only:
            print("- Diagnosis completed. Re-run without --diagnose-only to apply the recommended fixes.")
        else:
            print("- Restart Cursor completely and test the terminal/Agent again.")
            print("- If the popup still appears, inspect the latest Cursor logs and kernel AppArmor denies.")
            print("- Backups were stored under the backup_root path shown above.")

    def execute(self) -> int:
        self.ensure_root()
        self.detect_environment()
        self.scan_logs()

        if self.findings.apparmor_enabled is False:
            self.warnings.append("AppArmor appears disabled; this specific repair path may not fix your issue.")
        if self.findings.apparmor_enabled is None:
            self.warnings.append("Could not determine whether AppArmor is enabled.")

        if self.diagnose_only or os.geteuid() != 0:
            self.print_summary()
            return 0

        self.disable_stale_profile_if_needed()
        self.patch_local_profile()
        self.create_or_update_cursor_system_profile()
        self.ensure_helper_permissions()
        self.print_summary()
        return 1 if self.errors else 0


def parse_args():
    parser = argparse.ArgumentParser(
        description="Diagnose and repair Cursor terminal sandbox failures caused by AppArmor on Linux."
    )
    parser.add_argument(
        "--diagnose-only",
        action="store_true",
        help="Collect diagnostics only. Do not change files, reload AppArmor profiles, or chmod binaries.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    doctor = CursorSandboxDoctor(
        diagnose_only=args.diagnose_only,
        verbose=args.verbose,
    )
    try:
        return doctor.execute()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

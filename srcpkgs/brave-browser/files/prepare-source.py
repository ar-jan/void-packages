#!/usr/bin/python3
"""Apply Brave and Void patches to a Linux source archive, with resumable state."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


CHROMIUM_VERSION = "156.0.8078.80"


def check_versions(package, brave_version):
    if package["version"] != brave_version:
        raise RuntimeError(f"Brave source version {package['version']} does not match {brave_version}")
    chromium = package["config"]["projects"]["chrome"]["tag"]
    if chromium != CHROMIUM_VERSION:
        raise RuntimeError(
            f"Brave requires Chromium {chromium}, but the snapshot and patches target "
            f"{CHROMIUM_VERSION}; update the Chromium sources and patches together")


def run(*args, cwd, check=True):
    return subprocess.run(args, cwd=cwd, check=check, capture_output=True, text=True)


def apply(patch, root, state, key, allowed_missing=frozenset()):
    digest = hashlib.sha256(patch.read_bytes()).hexdigest()
    if key in state:
        if state[key]["sha256"] != digest:
            raise RuntimeError(f"Previously applied patch changed: {patch}")
        return

    # The Linux Chromium tarball omits other platforms and some test sources.
    # Only absent, pre-existing files may be excluded; new files still apply.
    old_paths = [line[6:].split('\t')[0] for line in patch.read_text().splitlines()
                 if line.startswith('--- a/')]
    # GNU patch tolerates mismatched destination names that git apply treats
    # as renames. None of the selected Void patches intentionally rename files.
    if key.startswith("void/"):
        old = None
        for line in patch.read_text().splitlines():
            if line.startswith("--- "):
                old = line[4:].split("\t")[0]
            elif line.startswith("+++ b/") and old and old.startswith("a/"):
                if old[2:] != line[6:].split("\t")[0]:
                    raise RuntimeError(f"Unexpected rename in Void patch: {patch}")
    missing = [name for name in old_paths if not (root / name).exists()]
    unexpected = set(missing) - allowed_missing
    if unexpected:
        raise RuntimeError(f"Missing input for {patch}: {sorted(unexpected)}")
    excludes = [f"--exclude={name}" for name in missing]
    args = ["git", "apply", "--whitespace=nowarn", *excludes]
    result = run(*args, "--check", str(patch), cwd=root, check=False)
    if result.returncode:
        reverse = run(*args, "--reverse", "--check", str(patch), cwd=root, check=False)
        if reverse.returncode:
            raise RuntimeError(f"Cannot apply {patch}:\n{result.stderr}")
        # An interruption after git apply but before journalling is recoverable.
    else:
        run(*args, str(patch), cwd=root)
    state[key] = {"sha256": digest, "excluded_missing_files": missing}
    print(f"Applied {key}" + (f" (omitted {len(missing)} absent files)" if missing else ""), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path)
    parser.add_argument("patches", type=Path)
    parser.add_argument("--brave-version", required=True)
    args = parser.parse_args()
    src = args.src.resolve()
    patches = args.patches.resolve()
    brave = src / "brave"
    package = json.loads((brave / "package.json").read_text())
    check_versions(package, args.brave_version)
    journal = src.parent / ".void-patches.json"
    state = json.loads(journal.read_text()) if journal.exists() else {}

    if not (src / ".git").exists():
        run("git", "init", "-q", cwd=src)

    def save():
        tmp = journal.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
        tmp.replace(journal)

    # This release differs from the complete .79 archive only in chrome/VERSION.
    chromium_patch = f"chromium-{CHROMIUM_VERSION}.patch"
    apply(patches / chromium_patch, src, state, "chromium-version")
    save()

    omitted = frozenset(
        line for line in (patches.parent / "chromium-omitted-files").read_text().splitlines()
        if line and not line.startswith("#"))
    for line in (brave / "patches/.repositories.cfg").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if not line.startswith("//") or ".." in Path(line[2:]).parts:
            raise RuntimeError(f"Invalid patch repository: {line}")
        relative = line[2:]
        root = src / relative
        # git apply must not discover the void-packages Git repository above us.
        if not (root / ".git").exists():
            root.mkdir(parents=True, exist_ok=True)
            run("git", "init", "-q", cwd=root)
        for patch in sorted((brave / "patches" / relative).glob("*.patch")):
            apply(patch, root, state, "brave/" + str(patch.relative_to(brave / "patches")),
                  omitted if not relative else frozenset())
            save()

    for patch in sorted(patches.glob("*.patch")):
        if patch.name != chromium_patch:
            apply(patch, src, state, "void/" + patch.name)
            save()

    # The version helper can generate GN metadata from an archive without Git
    # history if both the original and Brave version files are supplied.
    chromium = package["config"]["projects"]["chrome"]["tag"].split(".")
    version = package["version"].split(".")
    fields = ("MAJOR", "MINOR", "BUILD", "PATCH")
    (src / "chrome/VERSION.chromium").write_text(
        "".join(f"{k}={v}\n" for k, v in zip(fields, chromium)))
    (src / "chrome/VERSION").write_text(
        "".join(f"{k}={v}\n" for k, v in zip(fields, [chromium[0], *version])))
    subprocess.run(["python3", "build/util/version.py", "gen", "../chrome/VERSION"],
                   cwd=brave, check=True)


if __name__ == "__main__":
    main()

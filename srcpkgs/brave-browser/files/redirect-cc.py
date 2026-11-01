#!/usr/bin/python3
# Copyright (c) 2025 The Brave Authors. All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://mozilla.org/MPL/2.0/.
"""Apply Brave's Siso redirect_cc source selection when building with Ninja.

Adapted from brave/build/config/siso/brave_siso_config.star. Header overrides
continue to use Brave's -iquote flag. The compiler's depfile records the
selected source and the original source it includes.
"""

import os
from pathlib import Path
import sys


def redirect(args, overrides):
    for index, arg in enumerate(args):
        if arg not in ("-c", "/c") or index + 1 == len(args):
            continue
        source = args[index + 1]
        relative = None
        if source.startswith("../../"):
            relative = source[6:]
        elif source.startswith("gen/"):
            relative = source[4:]
        else:
            parts = source.split("/")
            if len(parts) > 1 and parts[1] == "gen":
                relative = "/".join(parts[2:])
        if relative is not None:
            candidate = overrides / relative
            if candidate.is_file():
                args[index + 1] = os.path.relpath(candidate)
        break
    return args


def main():
    # Installed at src/brave/tools/void/redirect-cc.py by the template.
    overrides = Path(__file__).resolve().parents[2] / "chromium_src"
    args = redirect(sys.argv[1:], overrides)
    if not args:
        raise SystemExit("usage: redirect-cc.py COMPILER [ARGS ...]")
    os.execvp(args[0], args)


if __name__ == "__main__":
    main()

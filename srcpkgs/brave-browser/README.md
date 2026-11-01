This package builds Brave 1.98.63 with Chromium 156.0.8078.80 from source for
x86_64 glibc. Graphical operation has been confirmed by the package user.
Headless DevTools tests passed for JavaScript, WebAssembly and the browser
sandbox. The command-line DOM dump has a session-restoration bug; the workaround
below passes, but the default invocation still hangs.

Upstream tracking: https://github.com/brave/brave-browser/issues/58627

That open issue also reports the failure with official Brave releases. Our
results therefore do not indicate a missing Void dependency or service key.

For a headless DOM dump, use an isolated profile and explicitly request
incognito mode:

```sh
brave_test_dir=$(mktemp -d /tmp/brave-dump-dom.XXXXXX)
brave_test_status=0

env -u BRAVE_FLAGS timeout --kill-after=5s 20s brave-browser \
  --headless --incognito --disable-gpu \
  --no-first-run --no-default-browser-check \
  --user-data-dir="$brave_test_dir/profile" \
  --timeout=5000 --dump-dom \
  'data:text/html,<p id="result">before</p><script>document.getElementById("result").textContent="DOM_OK"</script>' \
  >"$brave_test_dir/dom.html" \
  2>"$brave_test_dir/stderr.log" || brave_test_status=$?

printf 'exit=%s\nlogs=%s\n' "$brave_test_status" "$brave_test_dir"
cat "$brave_test_dir/dom.html"
```

Expect exit 0 and `<p id="result">DOM_OK</p>` in the serialized document.
Exit 124 indicates the external timeout. The browser's `--timeout=5000` limits
page loading once its command handler starts; it cannot bound a startup path
that bypasses that handler. The browser sandbox remains enabled.

The temporary profile prevents forwarding commands to an existing graphical
browser. Logs and the profile are retained in the printed directory for
inspection. Run each comparison with a new directory and reset the status
variable. Removing `--incognito` reproduces the failure with default settings.

Do not add `--incognito` automatically in the package launcher: callers may
deliberately use a persistent profile's cookies and storage. For automation
requiring a regular profile, disable session restoration in that dedicated
profile instead. To test that case, omit `--incognito` and insert these commands
after creating the new temporary directory, before starting the browser:

```sh
mkdir -p "$brave_test_dir/profile/Default"
printf '%s\n' '{"session":{"restore_on_startup":5}}' \
  >"$brave_test_dir/profile/Default/Preferences"
```

This creates Preferences only in a fresh test profile. Do not overwrite an
existing profile's Preferences file. The value 5 means open the new-tab page;
1 means restore the previous session.

Tests on 2026-11-01, all with fresh profiles and the sandbox enabled:

| Browser | Startup configuration | DOM dump result |
| --- | --- | --- |
| Packaged Brave 1.98.63 | Default | Running after 20 seconds; empty output |
| Packaged Brave 1.98.63 | Default plus `--incognito` | Exit 0; JavaScript-modified DOM |
| Packaged Brave 1.98.63 | `session.restore_on_startup=5` | Exit 0; JavaScript-modified DOM |
| Void Chromium 156.0.8078.79 | Default | Exit 0; JavaScript-modified DOM |
| Void Chromium 156.0.8078.79 | `session.restore_on_startup=1` | Running after 20 seconds; empty output |

Brave's default case also hung with a working D-Bus session. A package user
independently reproduced the default failure on the desktop. Screenshot and
PDF command switches are mentioned in the upstream report but were not tested
in this package investigation.

The Chromium comparison is useful additional evidence for the upstream issue:
the failure also occurs in Chromium when session restoration is enabled.
Brave exposes it by default because `browser/brave_profile_prefs.cc` sets
`prefs::kRestoreOnStartup` to `SessionStartupPref::kPrefValueLast`.

In Chromium's `chrome/browser/ui/startup/startup_browser_creator_impl.cc`,
`RestoreOrCreateBrowser()` returns early after a successful synchronous session
restore. This bypasses `OpenTabsInBrowser()`, which dispatches
`headless::ProcessHeadlessCommands()`. Debugger breakpoints confirmed that the
command handler was not reached in the failing Brave run.

A permanent fix belongs in browser startup handling: headless command execution
must reach its command handler even when session restoration is configured.
It should preserve the user's stored preference and regular graphical startup
behavior. Regression coverage should exercise the real startup path with
session restoration enabled, checking both DOM output and process exit. A
handler-only test or an incognito-only smoke test would miss this failure.

Contribute the session-preference comparison to the existing Brave issue and
coordinate a Chromium report or fix from there. This document records the
local findings; no upstream comment or new issue has been submitted from this
packaging session. No package revision bump or browser rebuild is needed for
this documentation and explicit invocation workaround.

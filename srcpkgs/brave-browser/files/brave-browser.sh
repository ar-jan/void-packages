#!/bin/sh
export CHROME_WRAPPER=/usr/bin/brave-browser
export CHROME_DESKTOP=brave-browser.desktop
exec /usr/lib/brave-browser/brave ${BRAVE_FLAGS} "$@"

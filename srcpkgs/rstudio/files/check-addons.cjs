// Check the actual installed Electron ABI, not the build host's Node ABI.
const assert = require('node:assert/strict');
const path = require('node:path');
const { createRequire } = require('node:module');
const load = createRequire(path.join(process.cwd(), 'package.json'));
assert.match(process.versions.electron, /^42\./);
assert.equal(typeof load('./src/native/desktop.node').cleanClipboard, 'function');
assert.equal(typeof load('./src/native/dock.node').setDockLabel, 'function');
assert.equal(typeof load('unix-dgram').createSocket, 'function');
load('msgpackr-extract');
for (const name of ['unix-dgram', 'msgpackr-extract']) {
  assert(Object.keys(require.cache).some(p =>
    p.includes(`/node_modules/${name}/build/Release/`) && p.endsWith('.node')));
}
console.log(`Native addons loaded with Electron ${process.versions.electron}`);

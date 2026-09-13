// Keep dependency versions locked, but run generation/rebuild explicitly.
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
// npm/Electron require semver without zero-padded month numbers.
pkg.version = process.env.RSTUDIO_VERSION.replace(/^(\d+)\.0*(\d+)\./, '$1.$2.');
pkg.scripts.package = 'electron-forge package';
delete pkg.scripts.postinstall;
fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2) + '\n');
const lock = JSON.parse(fs.readFileSync('package-lock.json', 'utf8'));
lock.version = pkg.version;
lock.packages[''].version = pkg.version;
fs.writeFileSync('package-lock.json', JSON.stringify(lock, null, 2) + '\n');

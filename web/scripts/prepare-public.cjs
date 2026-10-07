// Runs the Python data pipeline before every build and verifies its output.
// Fails loudly (non-zero exit) when the pipeline errors or the expected
// JSON files are absent from web/public/ afterwards.
const { execSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const webDir = path.resolve(__dirname, '..');
const publicDir = path.join(webDir, 'public');
const required = ['fleet.json', 'drift.json', 'alerts.json', 'stamp.json'];

function fail(message) {
  console.error(`[prepare-public] ERROR: ${message}`);
  process.exit(1);
}

try {
  execSync('python3 ../services/main.py build', { cwd: webDir, stdio: 'inherit' });
} catch (err) {
  fail('data pipeline failed (python3 ../services/main.py build). See output above.');
}

for (const name of required) {
  if (!fs.existsSync(path.join(publicDir, name))) {
    fail(`expected ${name} in web/public/ after pipeline run, but it is missing.`);
  }
}
console.log('[prepare-public] pipeline OK: fleet, drift, alerts, stamp present.');

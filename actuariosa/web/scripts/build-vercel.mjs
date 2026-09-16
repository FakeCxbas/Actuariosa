import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const cli = fileURLToPath(new URL('cli.js', import.meta.resolve('vinext')));
const result = spawnSync(process.execPath, ['--import', new URL('./graceful-build-exit.mjs', import.meta.url).href, cli, 'build'], {
  stdio: 'inherit',
  env: { ...process.env, VINEXT_STATIC_EXPORT: '1' },
});
process.exit(result.status ?? 1);



// Reads the hook event JSON from stdin and formats the file that was just edited.
// A formatting failure never blocks the agent.
import { execFileSync } from 'node:child_process';
let raw = '';
process.stdin.on('data', d => (raw += d));
process.stdin.on('end', () => {
  let file = '';
  try { file = JSON.parse(raw).tool_input?.file_path || ''; } catch { process.exit(0); }
  const run = (cmd, args) => { try { execFileSync(cmd, args, { stdio: 'ignore', shell: process.platform === 'win32' }); } catch {} };
  if (/[\\/]backend[\\/].*\.py$/.test(file)) run('uv', ['run', '--project', 'backend', 'ruff', 'format', file]);
  else if (/[\\/]frontend[\\/].*\.(ts|tsx|css|json)$/.test(file)) run('npx', ['prettier', '--write', file]);
  process.exit(0);
});

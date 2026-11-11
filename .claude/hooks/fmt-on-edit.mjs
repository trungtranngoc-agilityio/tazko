// Reads the hook event JSON from stdin and formats the file that was just edited.
// A formatting failure never blocks the agent.
// Paths are resolved from CLAUDE_PROJECT_DIR so the hook works whatever the current directory is,
// and prettier runs from frontend/ so it uses the pinned version and frontend/.prettierrc.json
// (--no-install: never download a different prettier).
import { execFileSync } from 'node:child_process';
import path from 'node:path';
let raw = '';
process.stdin.on('data', d => (raw += d));
process.stdin.on('end', () => {
  let file = '';
  try { file = JSON.parse(raw).tool_input?.file_path || ''; } catch { process.exit(0); }
  const root = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const run = (cmd, args, cwd) => {
    try { execFileSync(cmd, args, { cwd, stdio: 'ignore', shell: process.platform === 'win32' }); } catch {}
  };
  if (/[\\/]backend[\\/].*\.py$/.test(file)) {
    run('uv', ['run', '--project', path.join(root, 'backend'), 'ruff', 'format', file], root);
  } else if (/[\\/]frontend[\\/].*\.(ts|tsx|css|json)$/.test(file)) {
    run('npx', ['--no-install', 'prettier', '--write', file], path.join(root, 'frontend'));
  }
  process.exit(0);
});

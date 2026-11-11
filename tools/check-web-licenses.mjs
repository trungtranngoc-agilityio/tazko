// Checks the licenses of every package that ships in the web bundle
// (web/package.json "dependencies", followed transitively). Dev tools are not
// shipped and are not checked. Exit 1 on any license outside the allow-list.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ALLOWED = new Set(["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD"]);
const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "web");
const nm = path.join(web, "node_modules");

function ok(license) {
  if (!license) return false;
  // "(MIT OR Apache-2.0)" passes if any option is allowed; "AND" needs all.
  const expr = String(license).replace(/[()]/g, "");
  if (expr.includes(" AND ")) return expr.split(" AND ").every((p) => ok(p.trim()));
  return expr.split(" OR ").some((p) => ALLOWED.has(p.trim()));
}

const seen = new Map();
const bad = [];
function visit(name) {
  if (seen.has(name)) return;
  const file = path.join(nm, name, "package.json");
  if (!fs.existsSync(file)) {
    bad.push(`${name}: not installed (run npm --prefix web ci)`);
    seen.set(name, null);
    return;
  }
  const pkg = JSON.parse(fs.readFileSync(file, "utf8"));
  const license = typeof pkg.license === "object" ? pkg.license?.type : pkg.license;
  seen.set(name, license);
  if (!ok(license)) bad.push(`${name}@${pkg.version}: ${license ?? "no license field"}`);
  for (const dep of Object.keys(pkg.dependencies ?? {})) visit(dep);
}

const root = JSON.parse(fs.readFileSync(path.join(web, "package.json"), "utf8"));
for (const dep of Object.keys(root.dependencies ?? {})) visit(dep);

if (bad.length) {
  console.error("Web licenses not allowed:\n  " + bad.join("\n  "));
  process.exit(1);
}
console.log(`web licenses ok (${seen.size} shipped packages)`);

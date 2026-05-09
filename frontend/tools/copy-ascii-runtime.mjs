import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { basename, join, resolve } from "node:path";

const [, , sourceArg, targetArg] = process.argv;

if (!sourceArg || !targetArg) {
  console.error("Usage: node copy-ascii-runtime.mjs <source> <target>");
  console.error(`Received ${process.argv.length - 2} argument(s):`);
  for (const [index, value] of process.argv.slice(2).entries()) {
    console.error(`  ${index + 1}: ${value}`);
  }
  process.exit(2);
}

const source = resolve(sourceArg);
const target = resolve(targetArg);
const excluded = new Set(["node_modules", ".npm-cache", ".astro", "dist"]);

mkdirSync(target, { recursive: true });

for (const name of excluded) {
  rmSync(join(target, name), { recursive: true, force: true });
}

const entries = [
  "src",
  "astro.config.mjs",
  "package.json",
  "package-lock.json",
  "tsconfig.json",
  "README.md",
];

for (const entry of entries) {
  const from = join(source, entry);
  const to = join(target, basename(entry));
  if (!existsSync(from)) continue;
  rmSync(to, { recursive: true, force: true });
  cpSync(from, to, {
    recursive: true,
    force: true,
    verbatimSymlinks: false,
    filter: (path) => !excluded.has(basename(path)),
  });
}

console.log(`Copied frontend runtime to ${target}`);

import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, unlinkSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
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
const generatedDirs = [".astro", "dist"];
const dependencyMarker = join(target, ".deps.hash");
const dependencyRequiredMarker = join(target, ".deps-required");

mkdirSync(target, { recursive: true });

function hashFile(path) {
  if (!existsSync(path)) return "";
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

const dependencyHash = [
  hashFile(join(source, "package.json")),
  hashFile(join(source, "package-lock.json")),
].join(":");

const previousDependencyHash = existsSync(dependencyMarker)
  ? readFileSync(dependencyMarker, "utf8").trim()
  : "";
const shouldInstallDependencies =
  !existsSync(join(target, "node_modules")) || dependencyHash !== previousDependencyHash;

for (const name of generatedDirs) {
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

if (shouldInstallDependencies) {
  writeFileSync(dependencyRequiredMarker, dependencyHash);
} else {
  try {
    unlinkSync(dependencyRequiredMarker);
  } catch {}
}

console.log(`Synced frontend runtime to ${target}`);
console.log(
  shouldInstallDependencies
    ? "Dependencies need refresh."
    : "Dependencies are cached; npm install can be skipped.",
);

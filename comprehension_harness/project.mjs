/**
 * project.mjs — the project's root and its configuration, for the scripts that are plain JavaScript and start
 * in milliseconds (`map.mjs`, the edit hook, the map's log). `config.ts` is the same for the TypeScript tools,
 * and is the one that checks the file's shape and says what each key means.
 */
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

export const CONFIG_FILE = 'comprehension.config.json';
const HERE = dirname(fileURLToPath(import.meta.url));

/** The nearest folder above this file that holds the configuration: the repository root. Null when none does. */
export function findRoot() {
  for (let dir = HERE; ; dir = dirname(dir)) {
    if (existsSync(join(dir, CONFIG_FILE))) return dir;
    if (dirname(dir) === dir) return null;
  }
}

/** The root, the configuration, and the places and commands the scripts read from it. Throws with no configuration. */
export function readProject() {
  const root = findRoot();
  if (root === null) throw new Error(`no ${CONFIG_FILE} in a folder above ${HERE} — the tools read the project's layout from it`);
  const config = JSON.parse(readFileSync(join(root, CONFIG_FILE), 'utf8'));
  return {
    root,
    config,
    /** This folder, from the root: where the other tools are. */
    tools: relative(root, HERE),
    /** The map's snapshots. */
    mapDir: join(root, config.cache, 'map'),
    /** The stories of the last test run, from the root. */
    stories: `${config.cache}/stories`,
    /** The feature folders, from the root. */
    features: `${config.docs}/features`,
  };
}

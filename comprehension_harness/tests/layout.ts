/**
 * The layout the tools' own tests are written against: the `source` and `tests` sections a project's
 * `comprehension.config.json` would hold. The tests build their inputs by hand and read no project's
 * configuration, so they pass in whatever project the tools are copied into.
 */
import { layoutOf } from '../layout';

export const LAYOUT = layoutOf({
  source: {
    scan: ['src', 'shared', 'supabase', 'tests', 'specs'],
    app: ['src/'],
    product: ['src/', 'shared/', 'supabase/functions/'],
    words: ['src', 'tests'],
    mechanisms: ['src/lib/'],
    chips: [],
  },
  tests: {
    roots: ['tests/'],
    files: '^tests/.*\\.test\\.tsx?$',
    narrative: ['tests/narratives/'],
    browser: ['tests/e2e/'],
    journeys: '^tests/e2e/journeys/.*\\.journey\\.spec\\.ts$',
    server: { roots: ['tests/db/', 'tests/edge/'], namedIn: ['tests/e2e/journeys/', 'tests/server-steps/'] },
  },
});

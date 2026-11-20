import { fetchSnippets, loadSnapshot } from "./api";
import { DEMO_NAMES, parseSnapshot, parseSnippetList } from "./reader";
import type { Snapshot } from "./types";

// Demo_Snippet names in DEMO order. The list is defined once in reader.ts and re-exported here.
export const DEMO_ORDER: readonly string[] = DEMO_NAMES;

export type DemoSources = { sources: Record<string, string>; snapshot: Snapshot | null };

function hasOwn(obj: Record<string, string>, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(obj, key);
}

// Runs one loader and turns a rejection into null. The loaders in api.ts do not reject, but a rejection
// must never escape the source loading.
async function settle(load: () => Promise<string | null>): Promise<string | null> {
  try {
    return await load();
  } catch {
    return null;
  }
}

// Loads the demo sources in the order of design 6.6.
// 1. The Backend snippet list is used when it parses with parseSnippetList (Requirement 2, criterion 7).
// 2. The Snapshot is loaded and parsed on every mount, not only when a source is missing. The unreachable
//    path (design 6.5, Requirement 8, criterion 11) needs its records for recorded output. Its sources fill
//    the names still missing (Requirement 2, criteria 8 and 9).
// 3. C13: the Snapshot gives sources only when the whole file passes parseSnapshot. A bad record drops
//    the Snapshot sources too, and the snapshot value is null.
// A demo name with no source in either place stays missing. The page shows SOURCES_UNAVAILABLE for it.
export async function loadDemoSources(): Promise<DemoSources> {
  const sources: Record<string, string> = {};

  const snippetText = await settle(fetchSnippets);
  if (snippetText !== null) {
    const list = parseSnippetList(snippetText);
    if (list.ok) {
      for (const snippet of list.value) {
        sources[snippet.name] = snippet.source;
      }
    }
  }

  const snapshotText = await settle(loadSnapshot);
  let snapshot: Snapshot | null = null;
  if (snapshotText !== null) {
    const parsed = parseSnapshot(snapshotText);
    if (parsed.ok) {
      snapshot = parsed.value;
    }
  }

  if (snapshot !== null) {
    for (const name of DEMO_ORDER) {
      if (hasOwn(sources, name)) {
        continue;
      }
      const record = snapshot.records.find((candidate) => candidate.name === name);
      if (record !== undefined) {
        sources[name] = record.source;
      }
    }
  }

  return { sources, snapshot };
}

// Returns the source of a demo name, or null when the name has no source. The page uses a null result
// to show SOURCES_UNAVAILABLE (Requirement 2, criterion 10). This function shows no message itself.
export function sourceFor(sources: Record<string, string>, name: string): string | null {
  return hasOwn(sources, name) ? sources[name] : null;
}

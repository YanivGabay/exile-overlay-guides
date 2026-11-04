/**
 * Validate every route under every option combination, then write one
 * bundle per game to dist/<game>.json. Exits non-zero on any parse error
 * or on new warnings that are not listed in <game>/known-warnings.txt.
 *
 * Run: tsx scripts/build.ts [--check]
 */
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, readdirSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import {
  compileGuide,
  type Bandit,
  type GameData,
  type GuideOptions,
} from "@exile-overlay/route-engine";

const ROOT = new URL("..", import.meta.url).pathname;
const checkOnly = process.argv.includes("--check");

interface GameManifest {
  game: "poe1" | "poe2";
  gameVersion: string;
  title: string;
}

const DATA_FILES: Record<keyof GameData.Bundle, string> = {
  Areas: "areas.json",
  Quests: "quests.json",
  Gems: "gems.json",
  KillWaypoints: "kill-waypoints.json",
  Characters: "characters.json",
  GemColours: "gem-colours.json",
  AwakenedGemLookup: "awakened-gem-lookup.json",
  VaalGemLookup: "vaal-gem-lookup.json",
};

function readJson<T>(path: string): T {
  return JSON.parse(readFileSync(path, "utf8")) as T;
}

function loadGame(game: string) {
  const dir = join(ROOT, game);
  const manifest = readJson<GameManifest>(join(dir, "manifest.json"));
  const data = Object.fromEntries(
    Object.entries(DATA_FILES).map(([key, file]) => [
      key,
      readJson(join(dir, "data", file)),
    ]),
  ) as unknown as GameData.Bundle;

  const routeFiles = readdirSync(join(dir, "routes"))
    .filter((f) => f.endsWith(".txt"))
    .sort((a, b) => routeOrder(a) - routeOrder(b));
  const routes = routeFiles.map((f) => readFileSync(join(dir, "routes", f), "utf8"));

  const knownPath = join(dir, "known-warnings.txt");
  const known = new Set(
    existsSync(knownPath)
      ? readFileSync(knownPath, "utf8").split("\n").map((l) => l.trim()).filter((l) => l && !l.startsWith("#"))
      : [],
  );
  const campaign = readJson<{
    skillPointQuests: Record<string, { points: number; note: string }>;
    reminders?: { id: string; when: Record<string, unknown> }[];
    league?: { notes: { id: string; area?: string }[] };
  }>(join(dir, "campaign.json"));
  return { manifest, data, routes, routeFiles, known, campaign };
}

function routeOrder(file: string): number {
  const m = /(\d+)/.exec(file);
  return m ? Number(m[1]) : 0;
}

function optionMatrix(): GuideOptions[] {
  const out: GuideOptions[] = [];
  const bandits: Bandit[] = ["None", "Oak", "Kraityn", "Alira"];
  const flags = [true, false];
  for (const leagueStart of flags)
    for (const library of flags)
      for (const bandit of bandits)
        for (const trials of flags)
          for (const quicksilver of flags)
            for (const fiveLink of flags)
              for (const extras of flags) out.push({ leagueStart, library, bandit, trials, quicksilver, fiveLink, extras });
  return out;
}

let failed = false;
mkdirSync(join(ROOT, "dist"), { recursive: true });

for (const game of ["poe1"]) {
  const { manifest, data, routes, known, campaign } = loadGame(game);
  const seen = new Set<string>();
  let stepCount = 0;
  // Every id that campaign.json points at must exist in the game data.
  const areaIds = new Set(Object.keys(data.Areas));
  for (const r of campaign.reminders ?? []) {
    for (const key of ["reachedArea", "upcomingArea"] as const) {
      const v = r.when[key] as string | undefined;
      if (v && !areaIds.has(v)) {
        console.error(`[${game}] ERROR reminder ${r.id}: unknown area ${v}`);
        failed = true;
      }
    }
    const q = r.when.questDone as string | undefined;
    if (q && !data.Quests[q]) {
      console.error(`[${game}] ERROR reminder ${r.id}: unknown quest ${q}`);
      failed = true;
    }
  }
  type Tip = { text: string; verified?: boolean; sources?: string[] };
  const creditKeys = new Set(((campaign as { credits?: { key: string }[] }).credits ?? []).map((c) => c.key));
  for (const [area, list] of Object.entries((campaign as { zoneTips?: Record<string, Tip[]> }).zoneTips ?? {})) {
    if (!areaIds.has(area)) {
      console.error(`[${game}] ERROR zone tip: unknown area ${area}`);
      failed = true;
    }
    for (const tip of list) {
      if (typeof tip.verified !== "boolean") {
        console.error(`[${game}] ERROR zone tip ${area}: set "verified" (true only after checking in game)`);
        failed = true;
      }
      for (const src of tip.sources ?? [])
        if (!creditKeys.has(src)) {
          console.error(`[${game}] ERROR zone tip ${area}: source ${src} missing from credits`);
          failed = true;
        }
    }
  }
  for (const n of campaign.league?.notes ?? []) {
    if (n.area && !areaIds.has(n.area)) {
      console.error(`[${game}] ERROR league note ${n.id}: unknown area ${n.area}`);
      failed = true;
    }
  }
  for (const options of optionMatrix()) {
    const guide = compileGuide(routes, data, options);
    stepCount = Math.max(stepCount, guide.steps.length);
    // Every route variant must hand in every quest that gives a passive point.
    const handedIn = new Set<string>();
    for (const s of guide.steps)
      if (s.step.type === "fragment_step")
        for (const p of s.step.parts) if (typeof p !== "string" && p.type === "quest") handedIn.add(p.questId);
    for (const [q, info] of Object.entries(campaign.skillPointQuests)) {
      if (!handedIn.has(q)) {
        console.error(`[${game}] ERROR route skips passive-point quest ${q} (${info.note})  (options ${JSON.stringify(options)})`);
        failed = true;
      }
    }
    for (const log of guide.logs) {
      const key = `${log.type}: ${log.msg}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (log.type === "error") {
        console.error(`[${game}] ERROR ${log.msg}  (options ${JSON.stringify(options)})`);
        failed = true;
      } else if (!known.has(log.msg)) {
        console.error(`[${game}] new warning: ${log.msg}  (options ${JSON.stringify(options)})`);
        failed = true;
      }
    }
  }
  for (const msg of known)
    if (![...seen].some((k) => k.endsWith(msg)))
      console.warn(`[${game}] known warning no longer occurs, remove it: ${msg}`);

  // Passive tree names for the newest game version we have (tools/build_tree.py).
  const treeDir = join(ROOT, game, "tree");
  const treeFile = existsSync(treeDir) ? readdirSync(treeDir).filter((f) => f.endsWith(".json")).sort().at(-1) : undefined;
  const tree = treeFile ? readJson(join(treeDir, treeFile)) : null;
  const content = { routes, data, campaign, tree };
  const hash = createHash("sha256").update(JSON.stringify(content)).digest("hex").slice(0, 12);
  const bundle = {
    schema: 1,
    game: manifest.game,
    title: manifest.title,
    gameVersion: manifest.gameVersion,
    version: hash,
    builtAt: new Date().toISOString(),
    ...content,
  };
  console.log(`[${game}] ${routes.length} route files, up to ${stepCount} steps, version ${hash}`);
  if (!checkOnly) writeFileSync(join(ROOT, "dist", `${game}.json`), JSON.stringify(bundle));
}

if (failed) {
  console.error("validation failed");
  process.exit(1);
}

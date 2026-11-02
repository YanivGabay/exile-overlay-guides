# Exile Overlay guides

Leveling route content for [Exile Overlay](https://github.com/YanivGabay/exile-overlay).
The app downloads the bundles built from this repo, so route fixes ship without an app release.

## Layout

```
poe1/
  manifest.json        game, game version, title
  routes/act-N.txt     the route, one file per act (route language below)
  data/*.json          areas, quests, gems, ... used to validate and render the route
  known-warnings.txt   accepted validator warnings; anything new fails the build
scripts/build.ts       validates every option combination and writes dist/<game>.json
```

## Route language (short)

Each line is one step. Tokens in braces are checked against the game data:

- `{enter|1_1_2}` go to an area (by area id), `{waypoint|1_1_town}` use a waypoint, `{waypoint_get}`, `{portal|set}` / `{portal|use}`, `{logout}`
- `{quest|a1q1}` hand in a quest, `{kill|Hillock}`, `{arena|Name}`, `{quest_text|Glyph}`, `{dir|90}` (direction in degrees, 0 = north)
- `#sub text` adds a hint under the previous step
- `#ifdef LEAGUE_START` ... `#endif` (also `LIBRARY`, `BANDIT_KILL`, `BANDIT_OAK`, `BANDIT_KRAITYN`, `BANDIT_ALIRA`) for route options; nested blocks are indented by 4 spaces
- `# text` at the end of a line is a comment

The validator simulates the route: you can only enter connected areas, use waypoints you have, and so on.

## Contributing

1. Edit a route file.
2. `npm install`, then `npm run check`. It must pass.
3. Open a pull request describing what was wrong in game (act, zone, what happened).

Only submit content you wrote yourself (see NOTICE.md).

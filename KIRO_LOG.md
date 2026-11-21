
## Tier 2 UI/UX Overhaul & Browser Polish
- **Scope:** Studio layout, `CodePane` IDE card with `Expand / Collapse` (`Esc` to close) and vertical resize, inline `SnippetSelector` + primary `Run` toolbar, compact 3-column readable `Disclaimers` card (all 5 disclaimers + replayed-state notes always visible), responsive 32-bit register grid tiles without mid-word label breaks, and bordered `ViolationList` table.
- **Files:** `web/app/StudioPage.tsx`, `web/components/CodePane.tsx`, `web/components/RunControl.tsx`, `web/app/grid-timeline.css`.
- **Verification:** `npx tsc --noEmit`, `npm test`, `npm run build`, and live browser check on `http://127.0.0.1:3000`.

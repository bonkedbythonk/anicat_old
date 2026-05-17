## Summary

This PR contains a set of small hardening and packaging improvements made for review on a feature branch. None of these changes modify core user-visible behavior, but they improve robustness for the API sidecar and build/install flow.

Primary changes:
- Stream logs efficiently in the `status` router to avoid loading large files into memory.
- Platform-safe detection of `mpv` process (uses `pgrep` on POSIX or `tasklist` on Windows).
- Add `ANICAT_DISABLE_AUTO_UPDATE` env toggle and respect `AppConfig.general.check_for_updates` to opt-out of auto-update actions.
- Use canonical `VERSION` in FastAPI app metadata.
- Serve cached manga images with `FileResponse` to stream files from disk.
- Add a small `run_cmd()` subprocess helper used for safer `git` operations.
- Add `web` `export` script and update `scripts/install.sh` to run `next export` so `out/` exists for static copy.
- Add a basic CI workflow to run tests, `ruff`, `pyright`, and build the frontend.

## Checklist
- [ ] Run the API locally and validate `/api/status/health` and `/api/status/logs`
- [ ] Build and export the frontend: `cd web && npm ci && npm run build && npm run export`
- [ ] Run unit/integration tests locally: `python -m pytest -q`
- [ ] Verify installer script: `./scripts/install.sh --no-launch` (on macOS)
- [ ] Confirm no regressions in CLI/TUI flow

## Notes
- These edits are collected on branch `testbranch`. They are intentionally conservative but should be validated in a local/dev environment before merging to `main`.

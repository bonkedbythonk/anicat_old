# Anicat Versioning System — Audit & Improvement Report

**Date:** 2026-05-21  
**Versions analyzed:** 4.6.6 through 4.6.8  
**Author:** GitHub Copilot (audit from codebase + CI logs + git history)

---

## 1. Overview: How Versioning Works Today

Anicat's versioning spans **7 touchpoints** across 3 domains: developer tooling, CI/CD, and in-app update delivery. The current version is `4.6.8` (semantic: MAJOR.MINOR.PATCH).

### 1.1 The Canonical Source

`version.txt` at the repo root holds the canonical version string (`4.6.8`). All other files are derived from it.

### 1.2 Propagation Chain

```
version.txt  (canonical)
    |
    v
bump-version.sh  (runs on `pre-commit-msg` hook or manually)
    |
    +--> anicat_media/_version.py   __version__ = "4.6.8"  (baked into Python bytecode)
    +--> pyproject.toml             version = "4.6.8"
    +--> web/package.json           "version": "4.6.8"
    +--> web/src-tauri/tauri.conf.json  "version": "4.6.8"
    +--> flake.nix                  version = "4.6.8"
```

`_version.py` is the Python runtime source — it's imported by `constants.py` as `VERSION` and used everywhere (health endpoint, update checks, CLI help text). Because it's a `.py` file with a string literal, PyInstaller bakes it directly into the sidecar bytecode — no file I/O needed.

### 1.3 Conventional Commit Hook

`.githooks/prepare-commit-msg` parses the first line of each commit message:

| Prefix | Bump | Example |
|--------|------|---------|
| `fix:` | PATCH | `4.6.7 → 4.6.8` |
| `feat:` | MINOR | `4.6.0 → 4.7.0` |
| `feat!:` / `fix!:` / `BREAKING CHANGE:` | MAJOR | `4.0.0 → 5.0.0` |
| Anything else | None | `chore:`, `refactor:`, `docs:` |

The hook calls `scripts/bump-version.sh <new_version>` then runs `git add` on all 6 files to stage them. **However**, because it's a `prepare-commit-msg` hook (not `pre-commit`), the staged files sometimes don't make it into the commit that triggered the hook. This is a known recurring bug — see Section 3.1.

### 1.4 CI/CD: GitHub Actions

`.github/workflows/nightly.yml` triggers on push to `master` or `nightly`:

1. Builds Python sidecar (PyInstaller)
2. Builds Next.js frontend (static export)
3. Builds Tauri macOS DMG (`tauri-apps/tauri-action@v0`)
4. Creates a GitHub Release:

| Branch | Tag | Type | Auto-published? |
|--------|-----|------|-----------------|
| `master` | `v{VERSION}-stable` | Draft | **No** — must be manually published |
| `nightly` | `nightly` | Prerelease | Yes |

Before creating a new stable release, CI deletes ALL prior `-stable` releases and their tags. This ensures `releases/latest` always points to the most recent published release.

### 1.5 In-App Update System

Located in `anicat_media/api/routers/status.py`, the update system has three endpoints:

| Endpoint | Purpose | Cache |
|----------|---------|-------|
| `GET /status/health` | Returns `update_available` boolean | 15 minutes |
| `POST /status/check-update` | Manual check, returns `{status, update_available, message}` | None |
| `POST /status/update` | Triggers actual update (runs install script) | None |

**Detection mechanism (dual-path):**

- **Git installs** (dev environments with `.git/`): Runs `git fetch origin {branch}` then `git rev-list --count HEAD..origin/{branch}`. If count > 0, update available.
- **DMG/release installs** (end users): Calls GitHub Releases API. For `stable`: compares `v{VERSION}` tag to `latest_tag`. For `nightly`: compares `LAST_COMMIT_FILE` (written by install script) against `target_commitish` of the nightly release.

**Update execution:**

- Git installs: `git pull` + `bash scripts/install.sh --no-launch`
- macOS DMG installs: Runs `curl ... install_macos.sh | bash` which downloads the latest DMG, replaces `/Applications/Anicat.app`, removes quarantine, kills old processes, restarts.

### 1.6 Frontend UX

`SettingsView.tsx` shows:
- Current version string (from `health.current_version`)
- Update branch selector (`stable` / `nightly`)
- "Check for Updates" button → calls `checkUpdate()`
- When update found: "Update" button → calls `triggerUpdate()`
- "Updating..." overlay while update is in progress

`Sidebar.tsx` shows an orange dot on the Settings icon when `health.update_available` is true.

### 1.7 Install Script

`scripts/install_macos.sh` is the user-facing entry point:
- Detects `update_branch` from `~/Library/Application Support/anicat/config.toml`
- Calls GitHub Releases API to find latest DMG URL
- Downloads, mounts, copies to `/Applications`, unmounts
- Removes quarantine xattr
- Writes `LAST_COMMIT_FILE` for nightly tracking
- Kills old Anicat processes, restarts the app

---

## 2. Current Bugs & Pain Points

### 2.1 [CRITICAL] Stable releases are drafts — users never see them

When CI creates a `v4.6.8-stable` release, it's a **draft**. GitHub's `releases/latest` API returns the most recent **published** release, skipping drafts entirely. This means:

- The install script downloads `v4.6.6-stable` even after `v4.6.8-stable` was built
- The in-app update check says "up to date" because `_check_github_update()` sees the published `v4.6.6-stable` tag
- Every stable release requires a human to click "Publish" on the GitHub Releases page

**This is the root cause of the recurring "wrong version" bug.**

### 2.2 [HIGH] prepare-commit-msg hook timing issue

The `prepare-commit-msg` hook bumps version files during hook execution, but `git` has already snapshotted the index for the commit. The `git add` inside the hook stages the files for the *next* commit, not the current one. This means:

```
Actual commit:  feat: add mal sync     → committed with OLD version
Working tree:   4.6.8                  → bumped by hook but not committed
Next commit:    chore: bump to 4.6.8   → needed just to include the bump
```

This creates noise commits (`chore: bump to X.Y.Z`) and occasionally leaves the version stale for one commit cycle.

### 2.3 [HIGH] Release cleanup is atomic but fragile

CI deletes ALL prior `-stable` releases before creating the new one. If tauri-action fails to create the release (network issue, build failure after the delete step), there will be **zero** stable releases on GitHub. The install script will 404.

Additionally, `gh release delete --cleanup-tag` deletes both the GitHub Release and the Git tag. If the delete succeeds but the create fails, the tag is gone — manual recovery requires re-pushing the tag.

### 2.4 [MEDIUM] Two detection paths can disagree

- Git installs check `git rev-list` (local commits behind remote)
- DMG installs check GitHub Releases (whether a DMG was built)

These can diverge when:
- Commits are pushed but CI hasn't finished building the DMG yet → git says "update available" but there's nothing to download
- CI built a DMG but the release is still a draft → DMG install says "no update" because latest published release is old

### 2.5 [MEDIUM] Nightly update detection depends on a cache file

`LAST_COMMIT_FILE` (`~/Library/Caches/anicat/.last_commit`) is the only way nightly installs know which build they're running. If this file is:
- Missing (fresh install without running the install script)
- Corrupted
- Pointing to a commit that no longer exists (force-pushed nightly)

Then nightly update detection silently fails and the app always reports "up to date."

### 2.6 [LOW] macOS-specific sed in bump-version.sh

```bash
sed -i '' "s/^version = .*/version = \"$NEW_VERSION\"/" pyproject.toml
```

The `-i ''` syntax is macOS-only. On Linux, this would require `-i` without the empty string. Anyone developing on Linux would hit this.

### 2.7 [LOW] No Windows/Linux self-update

The `POST /status/update` endpoint only handles macOS DMG installs. Windows and Linux builds (if they existed) would have no automatic update path.

### 2.8 [LOW] No version displayed in-app

Looking at the frontend code, the `SettingsView` doesn't explicitly show the version number to the user. The `current_version` field is returned by the health endpoint but not surfaced in the settings UI in an obvious way. Users don't know what version they're on without checking logs.

---

## 3. Proposed Improvements

### 3.1 [Critical Fix] Auto-publish stable releases

**Problem:** Stable releases are drafts — users get the old version.

**Solution A (Recommended):** Publish stable releases automatically.

```yaml
# In nightly.yml, change:
echo "RELEASE_DRAFT=true" >> $GITHUB_ENV
# To:
echo "RELEASE_DRAFT=false" >> $GITHUB_ENV
```

Then remove the "delete all prior releases" logic. Instead, update a single stable release:

```yaml
# Instead of deleting ALL -stable releases:
# 1. Delete only the specific tag we're about to create (re-run safety)
gh release delete "${{ env.RELEASE_TAG }}" --yes --cleanup-tag || true
# 2. Create the new release (tauri-action)
# 3. No need to delete old releases — GitHub sorts by date
```

This keeps a release history while ensuring `releases/latest` always returns the newest one.

**Solution B (Conservative):** Keep drafts but update the install script to use the releases list API instead of `releases/latest`:

```bash
# Instead of:
LATEST_RELEASE=$(curl -s "https://api.github.com/repos/$REPO/releases/latest")
# Use:
LATEST_RELEASE=$(curl -s "https://api.github.com/repos/$REPO/releases?per_page=1")
```

This returns the most recent release even if it's a draft. But it requires a GitHub token for private repos.

### 3.2 [High Fix] Fix the prepare-commit-msg hook

**Problem:** Version bump files are staged but not included in the current commit.

**Root cause:** `prepare-commit-msg` runs after Git snapshots the index but before the commit message is finalized. `git add` in this hook stages for the *next* commit.

**Solution:** Switch to a `pre-commit` hook that modifies the working tree BEFORE the commit is snapshotted:

```bash
#!/usr/bin/env bash
# .githooks/pre-commit — Auto-bump version BEFORE commit is snapshotted

COMMIT_MSG_FILE="$1"
# Read the commit message from .git/COMMIT_EDITMSG
COMMIT_MSG=$(cat "$(git rev-parse --git-dir)/COMMIT_EDITMSG" 2>/dev/null || echo "")

# ... same bump logic ...

# Files are staged by `git add` AND they WILL be in the commit
# because the pre-commit hook runs before Git snapshots the index
```

Alternatively, keep `prepare-commit-msg` but use `git commit --amend --no-edit` inside the hook to include the bumped files in the same commit. This is messier but doesn't require changing the hook type.

### 3.3 [High Fix] Idempotent release creation

**Problem:** Deleting all releases before creating the new one is fragile.

**Solution:** Use an upsert pattern:

```bash
# 1. Delete the specific tag if it exists (for re-runs)
gh release delete "${{ env.RELEASE_TAG }}" --yes --cleanup-tag 2>/dev/null || true

# 2. Create the release (tauri-action does this)

# 3. After creation, delete OLDER -stable releases (not the one we just made)
gh release list --limit 100 --json tagName,name --jq '.[].tagName' \
  | grep -- '-stable$' \
  | grep -v "${{ env.RELEASE_TAG }}" \
  | while read -r old_tag; do
      gh release delete "$old_tag" --yes --cleanup-tag || true
    done
```

This ensures there's always at least one release (the current one) even if cleanup fails.

### 3.4 [Medium Fix] Unified update detection

**Problem:** Git and DMG detection paths can disagree.

**Solution:** Always use the GitHub Releases API for both paths. For git installs, still allow `git pull` as the update mechanism, but use the releases API for *detection*:

```python
def _check_github_update(update_branch: str) -> bool:
    # Works for both git and DMG installs
    # Compare current VERSION against latest release tag
    ...
```

Remove the git-specific `rev-list` path from `get_health()` and `check_for_updates()`. This eliminates the divergence.

### 3.5 [Medium Fix] Robust nightly tracking

**Problem:** `LAST_COMMIT_FILE` is a single point of failure.

**Solution:** Embed the commit SHA into the application at build time (similar to how `_version.py` embeds the version). Add a `_commit.py`:

```python
# Auto-generated by CI — do not edit manually.
__commit__ = "abc123def456"
```

This is set by CI during the build (using `${{ github.sha }}`). No file I/O needed at runtime. If `__commit__` is present, compare against `target_commitish` from GitHub Releases API. If absent (dev install), fall back to `git rev-list`.

### 3.6 [Medium Feature] In-app version display

**Problem:** Users don't know what version they're running.

**Solution:** Show the version prominently in SettingsView:

```tsx
// SettingsView.tsx — add a version section at the top
<div className="version-info">
  <span>Anicat v{health?.current_version || "unknown"}</span>
  <span className="branch-badge">{updateBranch}</span>
</div>
```

Also add the version to the sidebar footer or the app's title bar.

### 3.7 [Medium Feature] Changelog in update prompt

**Problem:** Users are asked to update but don't know what changed.

**Solution:** When an update is detected, fetch the release body from GitHub and display it:

```python
# status.py — enhance check-update response
release_info = res_data[0] if isinstance(res_data, list) else res_data
return {
    "status": "success",
    "update_available": True,
    "message": f"v{latest_version} is available!",
    "release_notes": release_info.get("body", ""),
    "release_url": release_info.get("html_url", ""),
    "version": latest_version,
}
```

### 3.8 [Low Fix] Cross-platform bump-version.sh

**Problem:** `sed -i ''` is macOS-only.

**Solution:**

```bash
# Detect OS and use appropriate sed syntax
if [[ "$OSTYPE" == "darwin"* ]]; then
    SED_INPLACE=("sed" "-i" "")
else
    SED_INPLACE=("sed" "-i")
fi
"${SED_INPLACE[@]}" "s/^version = .*/version = \"$NEW_VERSION\"/" pyproject.toml
```

### 3.9 [Future] Automatic background updates

**Problem:** Users must manually trigger updates from Settings.

**Solution (long-term):** Add an opt-in auto-update mode:
1. Backend checks for updates on startup and every 6 hours
2. If update found and `auto_update` config is enabled, download DMG in background
3. Show a notification: "Anicat v4.7.0 ready — restart to apply"
4. Use Sparkle framework (macOS native) or a custom solution

### 3.10 [Future] Rollback support

**Problem:** If an update breaks something, there's no easy way to go back.

**Solution:** Keep the last N DMGs in `~/Library/Caches/anicat/updates/`. Add a "Rollback to previous version" button in Settings that swaps the app bundle and restarts.

---

## 4. Summary: Priority Matrix

| Priority | Issue | Impact | Effort |
|----------|-------|--------|--------|
| **P0** | Stable releases are drafts — users get old version | Every end user affected | 1 line change in YAML |
| **P1** | prepare-commit-msg hook doesn't include bump in commit | Every push, developer friction | Switch to pre-commit hook |
| **P1** | Release cleanup deletes all before creating new | Risk of zero releases | Add grep -v exclusion |
| **P2** | Two update detection paths diverge | Confusing "update available" without DMG | Unify on Releases API |
| **P2** | Nightly LAST_COMMIT_FILE fragility | Nightly users miss updates | Embed commit SHA at build |
| **P2** | No in-app version display | Users don't know their version | Add to SettingsView |
| **P3** | macOS-only sed in bump-version.sh | Can't dev on Linux | OS detection |
| **P3** | No changelog in update prompt | Bad UX for update decision | Fetch release body |
| **P4** | No auto-update | Manual update friction | Background download + notify |
| **P4** | No rollback | Risky for early adopters | Keep previous DMG |

---

## 5. Recommended Implementation Order

1. **Fix P0 immediately** — change `RELEASE_DRAFT=true` to `false` in nightly.yml. This single change fixes the "wrong version" bug for all users.
2. **Fix P1 hook** — switch to `pre-commit` hook so bumps are always included.
3. **Fix P1 release cleanup** — add the grep exclusion so there's always a fallback release.
4. **Implement P2 items** — unified detection, embedded commit SHA, version display. These are quality-of-life improvements but not blockers.
5. **P3/P4 as time permits** — nice-to-haves that polish the experience.

---

## Appendix A: All Files Involved in Versioning

| File | Role | Updated by |
|------|------|------------|
| `version.txt` | Canonical version | `bump-version.sh` |
| `anicat_media/_version.py` | Python runtime version | `bump-version.sh` |
| `pyproject.toml` | Python package version | `bump-version.sh` |
| `web/package.json` | Node package version | `bump-version.sh` |
| `web/src-tauri/tauri.conf.json` | Tauri bundle version | `bump-version.sh` |
| `flake.nix` | Nix package version | `bump-version.sh` |
| `.githooks/prepare-commit-msg` | Auto-bump trigger | Manual |
| `scripts/bump-version.sh` | Version propagation | Called by hook |
| `.github/workflows/nightly.yml` | CI/CD release pipeline | Manual |
| `scripts/install_macos.sh` | User-facing installer | Manual |
| `anicat_media/api/routers/status.py` | Update detection + trigger | Manual |
| `anicat_media/core/constants.py` | Imports VERSION | Indirect (via `_version.py`) |
| `web/src/components/views/SettingsView.tsx` | Update UX | Manual |
| `web/src/lib/api.ts` | API client for update endpoints | Manual |
| `~/Library/Caches/anicat/.last_commit` | Nightly commit SHA | Install script |
| `~/Library/Caches/anicat/.update_in_progress` | Update flag file | Backend trigger |

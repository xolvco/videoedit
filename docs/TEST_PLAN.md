# Test Plan

This document defines the testing strategy for `videoedit`.

## Why we need this

The project is growing across several dimensions at once:

- manifest schemas
- planning logic
- FFmpeg command generation
- CLI entrypoints
- music-video specific assembly behavior

Without a test plan, it will be easy to add features faster than we can trust them.

## Testing goals

The test strategy should give us confidence that:

- manifests are valid and versioned correctly
- timecode logic is reliable
- planning logic resolves cuts and sections correctly
- FFmpeg command generation is predictable
- CLI commands remain thin and correct
- render workflows are stable enough for automation

## Test layers

### Layer 1: Unit tests

Focus:

- timecode parsing
- duration resolution
- manifest parsing
- defaults and override resolution
- metadata generation
- filter graph generation

These should be fast and should not require FFmpeg binaries or real media files unless absolutely necessary.

### Layer 2: Service tests

Focus:

- `VideoEditingService` planning behavior
- manifest-to-plan resolution
- output path handling
- validation of cut references and source references

These may use monkeypatching or fakes for `ffprobe` results.

### Layer 3: CLI tests

Focus:

- argument parsing
- command registration
- mapping CLI args to service calls
- required docs and tests coverage per command

These should stay lightweight and mostly avoid real renders.

### Layer 4: Integration tests

Focus:

- end-to-end manifest resolution
- FFmpeg command execution on tiny test media
- chapter metadata behavior
- gap and fade behavior
- normalization behavior once added

These should use very small generated or checked-in fixture media and run less often than unit tests.

### Layer 5: Golden workflow tests

Focus:

- realistic music-video pipeline examples
- source footage -> cuts -> timeline -> render plan -> output

These should verify that core workflows survive refactors.

## Test data strategy

We should separate test data into tiers.

### Tier 1: Pure data fixtures

Examples:

- inline JSON objects
- tiny manifest files
- resolved plan snapshots

Use for:

- schema tests
- parser tests
- planner tests

### Tier 2: Synthetic tiny media fixtures

Examples:

- 1-second or 2-second generated color clips
- short clips with audio tones
- clips with different resolutions or aspect ratios

Use for:

- FFmpeg integration tests
- normalization tests
- assembly tests

These should be generated or stored in a small test fixtures area.

### Tier 3: Workflow fixtures

Examples:

- one miniature multi-cut music-video scenario
- one split-screen scenario later
- one mixed-format normalization scenario later

Use for:

- golden workflow tests

## What we should test now

These are the immediate priorities.

### Manifest layer

- `version` is required
- invalid schema shapes are rejected
- duplicate source ids are rejected
- duplicate cut ids are rejected
- unknown source references are rejected
- unknown cut references are rejected
- `end` and `duration` cannot both be set
- defaults and section overrides resolve correctly

### Planning layer

- cut durations resolve from source duration correctly
- timeline sections resolve titles predictably
- timeline sections inherit gap and fade defaults
- timeline sections can override defaults
- chapter metadata start and end values are correct

### CLI layer

- every command parses expected arguments
- every command has docs and tests
- `assemble` reads versioned timeline manifests

## What we should test next

Once `plan` and `validate` exist:

- `plan` outputs stable, machine-readable resolved timelines
- `validate` returns useful failures for broken manifests
- output schemas for `plan` are documented and tested

Once normalization exists:

- clips with mismatched sizes can be normalized
- clips with mismatched frame rates can be normalized
- clips with missing or incompatible audio are handled predictably

Once split-screen exists:

- layout manifests resolve correctly
- panel scaling and positioning are correct
- mixed-resolution inputs compose reliably

## Suggested test directories

Recommended structure:

- `tests/unit/`
- `tests/service/`
- `tests/cli/`
- `tests/integration/`
- `tests/workflows/`
- `tests/fixtures/manifests/`
- `tests/fixtures/media/`

We do not need to migrate everything immediately, but this should be the target structure.

## Tooling plan

Primary tools:

- `pytest` for the test runner
- `monkeypatch` for service and process isolation
- fixture helpers for temporary manifests and media paths

Later options:

- snapshot testing for resolved plans
- optional FFmpeg-marked integration tests

## Execution plan

### Fast local checks

Run on every change:

- parser tests
- planner tests
- CLI tests

### Slower integration checks

Run before release or on CI:

- FFmpeg-backed integration tests
- golden workflow tests

## Release gates

Before calling a feature ready, we should have:

- code
- docs
- command coverage
- unit tests
- at least one relevant service or integration test for risky behavior

For render-affecting changes, we should also have:

- one integration test or golden workflow test

## Current gaps

Right now the project is still missing:

- normalization and mixed-format integration coverage
- deeper canvas scenarios with audio mixing, more panel counts, and mixed resolutions
- workflow/golden tests for more than the first canonical render paths
- a clearer long-term split for the parts of `videoflow` that still live outside `videoedit`

## Current reality after the refactor

The refactor changed test ownership:

- `videoedit` is the source of truth and now owns the meaningful behavioral tests
- `media-tools` runs smoke tests that verify wrapper exports and basic CLI wiring
- `video_editing_cli` runs smoke tests that verify command/docs coverage, manifest compatibility, and service import wiring
- `videoflow` still needs a clearer long-term testing split because only part of its surface moved into `videoedit`

Today `videoedit` also has:

- fixture-backed manifest files under `tests/fixtures/manifests/`
- reusable generated-media helpers under `tests/conftest.py`
- direct render-path tests for `render_timeline`, `render_playlist`, `render_canvas`, and `plan_render`
- FFmpeg-backed integration tests for timeline, playlist, and canvas rendering using tiny generated media
- golden workflow tests for timeline and playlist summary behavior

So the current suite is now beyond a basic migration checkpoint, but it is not yet the full end-state test architecture described above. The main thing still missing is deeper FFmpeg-backed integration coverage in `videoedit`, not more full legacy-suite duplication in the wrapper repos.

## Recommended next testing milestone

1. Expand the existing generated-media helpers for mixed-size and mixed-audio scenarios.
2. Add canvas integration coverage for audio mix and multi-panel layouts beyond the first two-panel path.
3. Add normalization coverage with mismatched inputs.
4. Add another golden workflow test for a miniature end-to-end edit pipeline.
5. Decide whether any FFmpeg-heavy integration tests should be grouped under an explicit slow marker later.


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

These should use very small fixture media and run less often than unit tests.

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

- a dedicated fixture strategy for media files
- FFmpeg-backed integration tests
- a `plan` command to test without rendering
- explicit validation command coverage
- workflow/golden tests

## Recommended next testing milestone

1. Install and use `pytest` in the project environment.
2. Add manifest fixture files under `tests/fixtures/manifests/`.
3. Add a `plan` command and test its output.
4. Add the first FFmpeg integration test using tiny generated media.
5. Add one golden workflow test for a miniature music-video pipeline.


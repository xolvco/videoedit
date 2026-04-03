# Release Checklist

This checklist is for preparing a real tagged release of `video-editing-cli`.

It is intentionally lightweight for now so the project can grow into it without slowing feature work too early.

## Before cutting a release

- Confirm the target release scope is clear.
- Update docs for any user-facing changes.
- Make sure examples still match the current workflow.
- Run the local test suite in the project `.venv`.
- Confirm GitHub Actions are green on `main`.
- Build the docs locally or confirm the docs workflow passes.

## Feature readiness

- The release contains the features expected for that milestone.
- Known limitations are documented honestly.
- Commands added in the release have:
  - implementation
  - tests
  - docs

## Concat workflow readiness

- Validate direct file concat still works.
- Validate folder-driven concat still works.
- Validate `--json-preview` still generates a usable scaffold.
- Validate `--playlist` still accepts the scaffold shape.
- Test one real-world concat workflow with actual media files.

## Manifest readiness

- `validate` succeeds for the supported manifest types.
- `plan` still resolves assembly manifests correctly.
- Example manifests are valid and up to date.
- Manifest docs reflect the supported fields and current limitations.

## Packaging and install notes

- Confirm the package installs with `pip install -e .[dev]`.
- Confirm the README installation steps still work.
- State clearly that FFmpeg and ffprobe are external system dependencies for now.
- Confirm the tested Python versions match `pyproject.toml` and CI.

## Docs site readiness

- `mkdocs build --strict` succeeds.
- Quickstart reflects the recommended path for new users.
- Command pages match the current CLI behavior.
- Links between guides and command docs work.

## Release metadata

- Choose the release version.
- Update version metadata if needed.
- Write short release notes:
  - what is new
  - who the release is for
  - known limitations
- Tag the release commit.
- Publish the GitHub release.

## Not yet required for the first alpha

- Bundled FFmpeg
- Desktop installer or packaged executable
- Full release automation
- Cross-platform binary distribution

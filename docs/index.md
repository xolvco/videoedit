# videoedit

`videoedit` is a reusable Python library and CLI for FFmpeg-backed editing workflows.

It is aimed at practical workflows such as:

- validating manifests before rendering
- planning assembly jobs without rendering
- normalizing mismatched footage before later assembly
- concatenating folders of clips quickly
- rendering playlist, timeline, and canvas manifests into final outputs

## Start here

- [Quickstart](QUICKSTART.md)
  Fastest first run for new users
- [CLI Usage](USAGE.md)
  Broader command-line and library workflows
- [Concat Playlist Guide](CONCAT_PLAYLIST_GUIDE.md)
  Manifest-focused playlist authoring with titles, fades, and spacers

## Main workflows

- [`validate`](commands/validate.md)
- [`plan`](commands/plan.md)
- [`concat`](commands/concat.md)
- [`assemble`](commands/assemble.md)
- [Normalize through the library API](USAGE.md#core-library-workflows)
- [Render canvas manifests](USAGE.md#render-a-canvas-manifest)

## Reference

- [Manifest formats](MANIFESTS.md)
- [Architecture](ARCHITECTURE.md)
- [Architecture session](ARCHITECTURE_SESSION.md)
- [Test plan](TEST_PLAN.md)


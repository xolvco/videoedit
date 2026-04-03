# Backlog

## Now

- Define versioned `cut-list` and `timeline` manifest schemas
- Add a `plan` command that resolves a manifest without rendering
- Add a `validate` command for manifests
- Refactor assembly logic into explicit planning objects
- Add one end-to-end example for a fast-beating music video workflow
- Turn the test plan into concrete fixture, integration, and workflow tests
- Make the library packaging goal explicit in docs and public API design
- Define preview/final render modes and initial publishing presets
- Implement the v1 output contract: rendered video, resolved plan JSON, and job/output manifest

## Next

- Support reusable cut references instead of only inline section source definitions
- Add defaults and overrides for section-level gaps and audio fades
- Add chapter marker and metadata validation
- Add clip normalization planning and rendering
- Add resolved plan JSON and job manifest outputs
- Add title overlay support at section starts
- Add dry-run output as JSON for other tools
- Add optional intermediate normalized clips and marker metadata outputs
- Define timing cue inputs for future cue-aligned editing

## Later

- Beat grid, narration cue, and marker import
- Transition presets
- Combine and prepare audio segments for more complex assemblies
- Split-screen and multi-panel video composition
- Add cue-aligned cut nudging around requested cut points
- Source clip libraries
- Shot selection manifests
- Batch render workflows
- Optional OpenAI-assisted planning in a separate project phase

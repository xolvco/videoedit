# Architecture Session

This document captures the current architecture direction for `videoedit` after the initial scaffold phase.

## Problem statement

The project is not trying to be a general-purpose NLE. It is trying to make fast-beating music video assembly easier to automate.

The main pain points it should solve are:

- cutting many short moments out of source footage
- expressing those cuts in human-readable data
- rearranging the resulting moments quickly
- normalizing mismatched inputs so they can be assembled together
- combining audio and video pieces in pipeline-friendly ways
- rendering timeline experiments without hand-writing FFmpeg commands
- exposing the workflow to other applications through a stable Python API
- preparing outputs for different publishing channels without rebuilding everything by hand

## Product thesis

FFmpeg is the engine. `videoedit` should be the orchestration layer that turns music-video editorial intent into validated, reusable render plans.

It should also be designed as a production backend for a future UI. The UI should decide what the editor wants to do. This library should perform the hard work reliably and repeatably.

That means the project should center on:

- timeline data models
- cut-list and assembly manifests
- normalization and composition planning
- render planning
- predictable CLI automation
- repeatable workflows for experimentation
- preview-to-final production workflows

## Primary user workflow

The core workflow should be:

1. Inspect source footage and audio.
2. Define cuts from one or more source files.
3. Store those cuts in readable JSON.
4. Assemble a new timeline from those cuts.
5. Normalize clips or audio when needed for compatibility.
6. Add gaps, fades, markers, and optional overlays.
7. Render a fast preview when needed.
8. Render the final deliverable for the target channel.

## Core domain model

The project should standardize around these concepts.

### `SourceAsset`

Represents an input media file.

Fields:

- `id`
- `path`
- `media_type`
- `duration_seconds`
- `metadata`

### `Cut`

Represents a selected moment from a source asset.

Fields:

- `id`
- `source_asset_id`
- `start`
- `end` or `duration`
- `label`
- `tags`

### `TimelineSection`

Represents a positioned unit in an assembled output.

Fields:

- `cut_id` or inline source reference
- `title`
- `title_style`
- `gap_after_seconds`
- `audio_fade_in_seconds`
- `audio_fade_out_seconds`
- `audio_mix_override`
- `marker`
- `overlay`

### `TimelineManifest`

Represents the full editorial plan for one output.

Fields:

- `version`
- `sources`
- `cuts`
- `sections`
- `defaults`
- `audio`
- `title_styles`
- `branding`
- `output`

### `RenderPreset`

Represents a target publishing or canvas configuration.

Fields:

- `id`
- `width`
- `height`
- `fps`
- `audio_sample_rate`
- `audio_channels`
- `fit_strategy`
- `codec_profile`

### `LookPreset`

Represents a named visual treatment for the assembled output.

Fields:

- `id`
- `description`
- `global_filter_strategy`
- `harmonization_strategy`

### `HarmonizationStrategy`

Represents the policy used to reduce distracting color jumps between adjacent clips.

Fields:

- `enabled`
- `strength`
- `scene_transition_behavior`

### `AudioMixPreset`

Represents the default audio relationship for an assembled output.

Fields:

- `id`
- `description`
- `music_level_policy`
- `source_audio_level_policy`
- `ducking_strategy`
- `normalization_strategy`

### `AudioMixOverride`

Represents a section-level exception to the default audio mix.

Fields:

- `mode`
- `fade_in_seconds`
- `fade_out_seconds`

### `AudioBed`

Represents a soundtrack or music track supplied for the assembly.

Fields:

- `path`
- `start`
- `offset`
- `gain_db`

### `TitleStyle`

Represents a reusable text-title style embedded in the manifest.

Fields:

- `id`
- `anchor`
- `offset_x`
- `offset_y`
- `font_family`
- `font_size`
- `color`
- `opacity`
- `max_width`
- `reveal_style`
- `accent_line`

### `AccentLine`

Represents an optional graphic line paired with a title.

Fields:

- `placement`
- `line_width`
- `thickness`
- `color`
- `opacity`

### `BrandingBug`

Represents a branding mark overlaid on the rendered output.

Fields:

- `path`
- `anchor`
- `offset_x`
- `offset_y`
- `width`
- `opacity`
- `start`
- `duration`

### `IntroCard`

Represents an opening title/background sequence before the main playlist or timeline.

Fields:

- `background_mode`
- `background_path`
- `duration`
- `titles`

### `ProgramTitle`

Represents one title shown on the opening title card.

Fields:

- `text`
- `size_preset`
- `font_family`
- `color`
- `opacity`
- `start`
- `duration`
- `anchor`

### `CreditsSequence`

Represents a simple end-of-video credits presentation.

Fields:

- `background_mode`
- `background_path`
- `page_duration`
- `anchor`
- `entries`

### `CreditEntry`

Represents one role/name pair in the credits.

Fields:

- `role`
- `name`
- `role_font_size`
- `name_font_size`

### `CopyrightFrame`

Represents the final copyright or legal closing notice shown after the main program and optional credits.

Fields:

- `text`
- `anchor`
- `font_family`
- `font_size`
- `color`
- `opacity`
- `background_mode`
- `background_path`
- `duration`

### `RenderMode`

Represents whether the output is optimized for speed or quality.

Fields:

- `preview`
- `final`

## Architectural stance

The project should be library-first and data-first.

### Library-first

All important behavior should live in reusable Python services before it appears in the CLI.

### Data-first

The primary artifact should be a human-readable JSON manifest, not ad hoc command flags alone.

### Pipeline-first

Commands should compose into workflows instead of acting like isolated utilities.

## Recommended layers

### Layer 1: Media adapters

Responsibility:

- run `ffmpeg` and `ffprobe`
- normalize process execution
- parse low-level metadata

Examples:

- `ffmpeg.py`

### Layer 2: Domain models

Responsibility:

- define source assets, cuts, sections, manifests, and render plans
- validate data
- convert timecode formats

Examples:

- manifest models
- timecode parsing
- cut validation

### Layer 3: Planning services

Responsibility:

- build cut plans
- build timeline plans
- resolve render presets
- resolve look presets and harmonization policy
- resolve audio bed, normalization, and section mix policy
- resolve title styles, branding bug placement, and intro card presentation
- resolve credits pagination and copyright closing-frame presentation
- compute chapter markers
- compute transitions, gaps, fades, and overlays
- optionally nudge cuts for cue-aligned timing later

Examples:

- `CutService`
- `TimelinePlanner`
- `RenderPlanner`

### Layer 4: Rendering services

Responsibility:

- convert plans into FFmpeg command graphs
- support preview and final render modes
- apply global look presets and clip-to-clip harmonization
- normalize and mix soundtrack audio with section audio according to policy
- render text titles, branding bugs, and intro-card overlays
- render credits pages and final copyright frame
- optionally create prepared intermediate assets
- render output
- optionally dry-run and print plans

### Layer 5: CLI

Responsibility:

- parse arguments
- load manifest files
- call library services
- print results

The CLI should stay intentionally thin.

## Command strategy

The current commands are useful building blocks, but the product should move toward a clearer workflow-oriented command set.

### Keep as low-level utilities

- `probe`
- `trim`
- `extract-audio`

### Reframe or evolve

- `concat`
  It should evolve from a raw join helper into a lightweight sequence builder for playlist-style outputs.
  It is still not the main orchestration primitive, but it should support practical editorial features such as:
  - folder or file-list driven sequencing
  - simple global clip trimming
  - optional interstitial spacers between clips
  - optional clip-start markers for navigation
  - a playlist JSON mode for per-item timing and transition control

- `assemble`
  This should become the central render command for timeline manifests.

### Add next

- `plan`
  Load a manifest and print the resolved timeline without rendering.

- `cuts validate`
  Validate a cut list or timeline manifest.

- `normalize`
  Prepare clips so different media can be assembled safely.

- `render`
  Build preview or final outputs from a resolved timeline and preset.

- `cuts render`
  Materialize cut files if a workflow needs explicit intermediates.

- `timeline render`
  Potential long-term rename of `assemble` if the manifest model grows.

## Manifest strategy

The project likely needs two related JSON forms.

### 1. Cut list manifest

Purpose:

- define reusable moments extracted from source footage

Example shape:

```json
{
  "version": 1,
  "sources": [
    { "id": "session", "path": "session.mp4" }
  ],
  "cuts": [
    {
      "id": "intro-look",
      "source": "session",
      "start": "00:00:05.000",
      "end": "00:00:06.200",
      "label": "Intro glance"
    }
  ]
}
```

### 2. Timeline manifest

Purpose:

- define how cuts are assembled into one output

Example shape:

```json
{
  "version": 1,
  "defaults": {
    "gap_after_seconds": 0.15,
    "audio_fade_in_seconds": 0.04,
    "audio_fade_out_seconds": 0.04
  },
  "audio": {
    "music_path": "track.wav",
    "mix_preset": "music-led"
  },
  "sections": [
    {
      "cut": "intro-look",
      "title": "Intro"
    },
    {
      "cut": "ambient-break",
      "title": "Ambient break",
      "audio_mix_override": "source-only"
    }
  ],
  "output": {
    "path": "output.mp4"
  }
}
```

### 3. Concat playlist manifest

Purpose:

- define a linear playlist-style sequence from source videos with simple per-item timing and navigation metadata

Example shape:

```json
{
  "version": 1,
  "defaults": {
    "spacer_mode": "black",
    "spacer_seconds": 2.0,
    "audio_fade_in_seconds": 0.35,
    "audio_fade_out_seconds": 0.35
  },
  "title_styles": {
    "clean-lower-left": {
      "anchor": "bottom-left",
      "font_family": "Aptos",
      "font_size": 42,
      "color": "#FFFFFF",
      "opacity": 0.92,
      "reveal_style": "static",
      "accent_line": {
        "placement": "above",
        "line_width": 220,
        "thickness": 3,
        "color": "#FFFFFF",
        "opacity": 0.92
      }
    }
  },
  "branding": {
    "bug": {
      "path": "branding/bug.png",
      "anchor": "top-right",
      "width": 180,
      "opacity": 0.8
    },
    "intro_card": {
      "background_mode": "black",
      "duration": 4.0,
      "titles": [
        {
          "text": "Summer Mix 2026",
          "size_preset": "huge",
          "anchor": "center"
        }
      ]
    }
  },
  "credits": {
    "background_mode": "color",
    "page_duration": 4.0,
    "anchor": "center",
    "entries": [
      {
        "role": "Performer",
        "name": "Ava"
      },
      {
        "role": "Edited by",
        "name": "Bruce Kyle"
      }
    ]
  },
  "copyright": {
    "text": "Copyright 2026 Xolv LLC. All rights reserved.",
    "anchor": "bottom-center",
    "font_size": 18,
    "color": "#FFFFFF",
    "opacity": 0.9,
    "background_mode": "black",
    "duration": 3.0
  },
  "items": [
    {
      "path": "clips/intro.mp4",
      "start": "00:00:03.000",
      "end": "00:00:18.000",
      "marker": "Intro",
      "title": "Ava",
      "title_style": "clean-lower-left"
    },
    {
      "path": "clips/topic-a.mp4",
      "start": "00:00:10.000",
      "end": "00:00:45.000",
      "audio_fade_in_seconds": 0.5,
      "audio_fade_out_seconds": 0.5,
      "marker": "Topic A"
    }
  ],
  "output": {
    "path": "playlist.mp4"
  }
}
```

## Key design decisions

### Decision 1

The main product artifact should be JSON manifests, not only imperative CLI flags.

Reason:

- easier for humans to read
- easier for apps to generate
- easier to diff in git
- easier to validate

### Decision 2

The system should prefer references to reusable cuts over duplicating inline source declarations everywhere.

Reason:

- supports experimentation
- reduces repeated timing edits
- creates cleaner timelines

### Decision 3

Rendering and planning should be separate modes.

Reason:

- users need to inspect timeline decisions before long renders
- other tools may want the resolved plan without rendering

### Decision 4

Overlays and beat-aware features should build on the manifest layer, not bypass it.

Reason:

- keeps the product coherent
- prevents feature sprawl

### Decision 8

Timing alignment should not be treated as music-only.

Reason:

- music beats, narration beats, sentence timing, emphasis points, and demo moments are all timing cues
- the same cut list may need to be tried against different timing tracks
- cue-aligned editing is a broader and more valuable capability than music-only beat matching

### Decision 5

The library should optimize for production reliability because it is expected to sit behind a user-facing UI.

Reason:

- UI features are only trustworthy if the backend behavior is predictable
- users should be able to describe hard edits without manually fixing every render
- packaging as a reusable artifact requires stable library boundaries

### Decision 6

The library should support both preview and final rendering workflows.

Reason:

- users need fast iteration while deciding on cuts and assembly
- final renders may require heavier normalization, quality, or downstream enhancement
- preview-to-final flow fits a UI-driven production workflow much better than single-pass rendering

### Decision 7

Publishing targets should begin as named presets.

Reason:

- presets are easier for users and future UI flows
- presets help keep pipeline behavior consistent
- explicit raw output settings can be added later as an advanced escape hatch

### Decision 9

Look presets should automatically include color harmonization by default.

Reason:

- fast-cut edits should feel cohesive without forcing the user to tune color controls first
- the library should reduce distracting color jumps between clips as part of doing the obvious thing
- users can opt out, but the default path should favor speed and visual continuity

### Decision 10

V1 color work should target continuity and style, not full lighting repair.

Reason:

- reducing visual whiplash between clips is a practical and testable first step
- full bad-lighting correction is a deeper grading problem and can come later
- preset-driven continuity fits the current library-first, workflow-first direction

### Decision 11

Audio should default to a global mix preset with section-level overrides.

Reason:

- most fast-cut edits want one overall audio intent rather than hand-mixing every section
- some sections still need explicit exceptions such as ambient-only or music-only moments
- this keeps the common workflow fast while preserving editorial control where it matters
- in v1, these exceptions should be assigned per clip or section as the timeline is assembled

### Decision 12

The library should support music-plus-source-audio workflows, not just one audio source.

Reason:

- assembled videos often combine a soundtrack, source ambience, and occasional call-to-action or scene-driven audio
- users need the library to manage the default blend rather than manually rebuilding the mix for each cut
- audio behavior belongs in assembly planning and rendering, not scattered across low-level utilities

### Decision 13

`concat` should support both quick file-list mode and a playlist JSON mode.

Reason:

- users often need a fast way to jam videos together into a playlist-style output
- a JSON playlist gives a clear upgrade path for per-clip timing, markers, and transitions without creating a separate command
- both modes still represent the same core intent: build one linear sequence from many videos

### Decision 14

`concat` markers should apply only to clips and should land at the clip start in the final output timeline.

Reason:

- navigation markers are most useful for jumping to real content, not blank spacers
- playlist-style outputs benefit from chapter-like navigation to favorite segments
- clip timing remains source-relative while marker placement is resolved on the final assembled timeline

### Decision 15

V1 titles should be text-first, restrained, and style-driven.

Reason:

- most built-in motion-title presets in editors are visually noisy and not a good default for this product
- users need a clean way to label performers, clips, and sequences without gimmicky animation
- reusable title styles embedded in the manifest make experimentation portable and easier to manage

### Decision 16

V1 title styles should live inside the manifest, not in separate style files.

Reason:

- too many sidecar files are easy to mishandle
- keeping styles with the edit plan improves portability and reuse
- embedded styles are simpler to validate, copy, and version

### Decision 17

Branding bugs and opening title cards should be modeled separately from clip titles.

Reason:

- clip titles, persistent branding, and whole-program titling are different editorial concepts
- separate models keep defaults simple while still supporting real publishing workflows
- shared positioning and styling conventions still allow the system to feel consistent

### Decision 18

V1 credits should be simple paged cards, not rolling or table-based layouts.

Reason:

- clean static or paged credits are easier to make look good consistently
- stacked role/name pairs fit the v1 goal of tasteful defaults without complex layout logic
- multi-column layouts, dotted leader lines, and richer credit choreography can come later

### Decision 19

Copyright should be modeled as a separate final closing frame.

Reason:

- copyright is a legal or brand notice, not the same thing as editorial credits
- a dedicated closing frame is clearer and easier to reuse in commercial workflows
- keeping it separate avoids overloading the credits layout with unrelated responsibilities

## Output contract

Recommended primary outputs:

- rendered video
- resolved plan JSON
- job/output manifest for the next pipeline step

Recommended optional outputs:

- prepared intermediate clips
- chapter or marker metadata
- preview renders

V1 should treat the primary outputs above as the default contract. Optional outputs can be enabled when a workflow or downstream pipeline step needs them, but they should not define the first public interface.

## Initial preset direction

The first preset strategy should prefer named outputs rather than fully raw technical settings.

Examples:

- `standard_16_9`
- `vertical_9_16`
- `custom_wide_20_9`

The custom wide preset is especially important because it reflects the intended visual language of the product rather than only standard platform formats.

## Scoped roadmap

### V1

V1 should focus on the production backbone for repetitive assembly work.

Goals:

- accept reviewed JSON manifests as the main public interface
- normalize clips enough that mismatched media can be assembled safely
- assemble whole clips and cut segments into a final sequence
- support playlist-style concat workflows for combining many videos into one navigable output
- support repeated editorial structure like gaps, fades, and markers
- support preview and final render modes
- support global look presets that automatically harmonize clip-to-clip color continuity
- support global audio mix presets with section-level overrides
- produce the v1 output contract:
  - rendered video
  - resolved plan JSON
  - job/output manifest
- support named render presets, including:
  - `standard_16_9`
  - `vertical_9_16`
  - `custom_wide_20_9`
  - cinema-wide presets

V1 is not trying to replace an editor. It is trying to make repetitive, structured assembly much faster and more reliable.

Initial look direction:

- apply named look presets at the assembly/render level
- automatically pair each look preset with default-on harmonization
- allow an explicit opt-out for users who do not want harmonization
- focus on reducing scene-to-scene color whiplash, especially in short, fast-cut sequences
- defer advanced lighting repair and custom JSON palette definitions to later versions

Initial audio direction:

- let the user choose one overall audio mix preset for the assembled output
- support soundtrack plus source-audio workflows
- normalize and blend audio automatically according to the selected preset
- allow clip-level section overrides for moments like ambient-only, music-only, or source-led scenes
- keep v1 overrides simple, with section-scoped behavior and optional fade-in/fade-out timing
- support both manifest-defined music inputs and CLI overrides for quick experimentation

Initial concat direction:

- keep `concat` as one command with two input modes:
  - direct file-list mode for quick assembly
  - playlist JSON mode for refined sequencing
- default to no markers
- support `--markers` in quick mode to generate clip-start markers from normalized filenames
- keep spacer behavior global in v1, with `black` as the first spacer mode
- allow playlist items to define source-relative start/end timing and simple per-item audio fade overrides
- reserve more advanced per-item spacer behavior, internal markers, and title treatment for later versions

Initial title and branding direction:

- support one text title per clip or section in v1
- keep native titles text-only with transparent rendering over video
- support restrained reveal styles such as `static` and `typewriter`
- support reusable `title_styles` embedded directly in the manifest
- use anchor-based positioning with offsets for iterative layout tuning
- support an optional accent line with placement above, below, left, or right of the text
- support a manifest-level branding bug using a transparent PNG with size, placement, opacity, and timing
- support an optional intro card with a black background by default and an optional branded video background
- support one or more program titles on the intro card using simple size presets such as `huge`, `medium`, and `subdued`
- support optional simple paged credits on a color, image, or video background
- support a separate final copyright frame with small anchored text on a closing screen

### V2

V2 should extend the backbone into more differentiated composition and timing capabilities.

Goals:

- large-scale clip recombination
- split-screen and multi-panel composition
- uneven panel sizing and sliced layouts
- richer audio combination workflows
- richer audio automation such as more detailed ducking, envelope control, and advanced mix shaping
- optional prepared intermediates for safer editing and reuse
- cue-aligned cut resolution
- deeper color tooling such as advanced correction and custom palette definitions

V2 presentation refinement should include:

- multiple titles per clip or section instead of only one
- more detailed title timing and layout control
- optional overlay media for advanced custom title treatments
- richer scheduling for branding bugs beyond simple start/duration behavior
- side-by-side or table-based credits layouts
- dotted leader-line or other more stylized credit treatments
- more advanced copyright and legal closing layouts

V2 audio refinement should include:

- more fine-grained timing within clips instead of only section-level overrides
- richer gain envelopes and automation beyond simple fades
- more detailed mix shaping per scene moment when needed

Cue alignment means:

- a user provides a proposed cut list and reassembly
- another tool provides a list of timing cues
- the library resolves or nudges cuts so the edit aligns more naturally with those cues

Timing cues can include:

- music beats
- narration beats
- sentence boundaries
- emphasis points in spoken script
- product demo moments

This should eventually let users try alternate edits against alternate music or narration tracks without rebuilding the whole sequence by hand.

## Risks

### Risk: too generic

If the project keeps adding generic FFmpeg helpers, it will lose focus.

Mitigation:

- prioritize music-video editorial workflows
- treat generic commands as utilities, not the product center

### Risk: too much rendering logic in CLI commands

Mitigation:

- move real behavior into planning and service layers

### Risk: manifest drift

Mitigation:

- version the manifest format
- add explicit validators
- add dry-run inspection output

## Recommended next milestone

The next architecture milestone should be:

1. Define versioned manifest schemas.
2. Add `plan` and `validate` commands.
3. Split inline assembly logic into explicit planning objects.
4. Add one workflow example that starts from source clips and ends with a rendered music-video timeline.


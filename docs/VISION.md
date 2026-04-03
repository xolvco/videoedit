# Vision

`videoedit` exists to help create fast-beating music videos and other highly structured video assemblies that are hard to build quickly in traditional editors.

## Core outcome

The CLI should make it easy to take raw source footage, cut it into precise moments, and reassemble those moments into energetic timelines that can later be refined by hand or driven by other tools.

In the longer term, this package should function as a production library behind a UI. The UI can handle selection and creative control, while this library handles the difficult orchestration, normalization, planning, and rendering behavior.

The practical goal is multi-channel publishing. A user should be able to use this library to help produce outputs for places like:

- YouTube
- TikTok
- product sales and product demo videos
- real-estate video sites
- help and support videos

## What "fast-beating music videos" means here

In practice, this project should help with workflows like:

- cutting footage into short, high-energy sections
- rearranging clips to match song structure or beat plans
- normalizing different clips so they can be assembled together reliably
- adding brief black gaps or separators between visual phrases
- softening joins with audio fades where needed
- combining or preparing audio portions for assembly
- marking sections with readable titles and metadata
- eventually dividing the frame into multiple sections for simultaneous playback
- producing quick preview renders before committing to final output
- later aligning cuts against timing cues such as music beats or narration beats
- exposing everything through JSON so other apps can generate or transform timelines

## Product direction

The library should prioritize:

- human-readable manifest formats
- reliable CLI automation for pipelines
- reusable Python APIs for other applications
- predictable FFmpeg command generation
- features that support editorial speed, iteration, and experimentation
- production-friendly behavior that can safely sit behind a user interface
- outputs that can be tailored for multiple publishing targets through presets

## Near-term feature ideas

- dry-run timeline inspection before rendering
- beat grid, narration cue, or marker import
- clip normalization workflows
- reusable transition presets
- title overlays for section starts
- split-screen and multi-panel composition
- preview and final render modes
- source clip libraries and shot selection manifests


# Adding a Command

Every CLI command in this project should ship with three things in the same change:

1. The command implementation
2. A test module
3. A documentation page

## Required layout

- CLI implementation: `src/video_editing_cli/commands/<command_name>.py`
- Tests: `tests/test_<command_name>.py`
- Docs: `docs/commands/<command_name>.md`

Use underscores in filenames for multi-word commands. For example, the `extract-audio` command maps to:

- `src/video_editing_cli/commands/extract_audio.py`
- `tests/test_extract_audio.py`
- `docs/commands/extract_audio.md`

## Checklist

Before a command is considered done, make sure it has:

- a parser registration function
- a handler function
- at least one focused test covering parsing or behavior
- a documentation page with purpose, arguments, and examples

The test suite includes a guard that fails if a registered command is missing its matching test or docs page.

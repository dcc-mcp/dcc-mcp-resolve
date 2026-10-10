# Host validation records

This directory holds evidence from runs against a **real DaVinci Resolve
installation**.

## Why this directory exists

Current CI runs contract checks, lint, packaging and a host-free pytest suite.
It does not launch DaVinci Resolve, because the external transport needs a
Studio licence and the in-process transport needs a GUI session. Anything that
touches the scripting API needs host validation, and that evidence lives here.

A green CI run is **not** evidence that host behaviour works.

## What is not verified by CI

- Any call into the Resolve scripting API (`scriptapp`, `GetProjectManager`,
  `GetMediaPool`, `GetTimelineByIndex`, `GetGallery`, and so on).
- The Studio-only external-scripting gate against a real free-edition host.
- Scripting-directory and `fusionscript` library discovery on a real install.
- Real render, deliver and project-mutation behaviour.

## How to record a validation

Add a dated Markdown file plus its JSON result, following the shape used by
sibling adapters:

| File | Contents |
|---|---|
| `<topic>.md` | What was run, on which Resolve version, edition and OS, and what was observed |
| `<topic>.json` | Machine-readable result: host version, edition, transport, timestamp, pass/fail per check |

State the Resolve version, **the edition (Studio or free)**, the OS, the
transport used, and the adapter version. The edition matters: it is what makes
an external-transport result reproducible at all.

Record failures as failures — an untested path is not a tested path. Do not
redistribute Resolve binaries, installers, licence keys or the vendor's
scripting documentation with a record.

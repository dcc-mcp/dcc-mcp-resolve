# Changelog

## 0.1.0 (2026-10-11)

### Features

- Initial release of the DaVinci Resolve adapter for DCC-MCP.
- External scripting transport (default) and in-application script transport,
  selected through `DCC_MCP_RESOLVE_TRANSPORT`.
- Studio-only external scripting gate: `doctor` reports `host_edition` and
  `external_scripting_allowed`, and stages a free-edition host on the external
  transport as a transport failure with a `switch-to-in-process` next step.
- Five read-only inspection skills: `resolve-session`, `resolve-project`,
  `resolve-media-pool`, `resolve-timeline`, `resolve-gallery`.
- `dcc-mcp-resolve doctor` readiness report validated against the Install SOP
  schema published by `dcc-mcp-core`.

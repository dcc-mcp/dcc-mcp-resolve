# Changelog

## [0.1.2](https://github.com/dcc-mcp/dcc-mcp-resolve/compare/v0.1.1...v0.1.2) (2026-10-17)


### Bug Fixes

* respect free Resolve 21.1 Python scripting restriction ([#2](https://github.com/dcc-mcp/dcc-mcp-resolve/issues/2)) ([36ff09c](https://github.com/dcc-mcp/dcc-mcp-resolve/commit/36ff09c5efed77242ab5de02809c3cb8c777396b))

## [0.1.1](https://github.com/dcc-mcp/dcc-mcp-resolve/compare/v0.1.0...v0.1.1) (2026-10-10)


### Features

* DaVinci Resolve adapter with external and in-process transports ([befd93b](https://github.com/dcc-mcp/dcc-mcp-resolve/commit/befd93bc6dcd5d5231d5e38f31cbd8771d02ed45))

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

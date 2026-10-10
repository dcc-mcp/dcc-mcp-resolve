# Installing dcc-mcp-resolve

Install the package first, then do the host-side setup for the transport you
intend to use.

```bash
pip install dcc-mcp-resolve
```

Check what the adapter can see at any time:

```bash
dcc-mcp-resolve doctor
```

The report's `host_available` field tells you whether Resolve is reachable. It
is `false` until the host-side setup below is complete — that is expected, not
an error.

## Pick a transport first

**External scripting is a DaVinci Resolve Studio feature from Resolve 19.1
onward.** On the free edition, skip to [Transport 2](#transport-2-in-process-scripts):
the `external` transport cannot work, and no amount of configuration changes
that.

The `doctor` output settles it:

- `host_edition` — `studio` or `free`.
- `external_scripting_allowed` — `true`, `false`, or `null` when the host
  version could not be read.

## Transport 1: external scripting (default, Studio)

The adapter runs in its own process and connects to a running Resolve.

### 1. Locate the scripting directory and library

Resolve installs a `Developer/Scripting` directory and a `fusionscript` library.
The adapter searches the documented defaults for your platform, and honours two
environment variables when your install is elsewhere.

Windows:

```bat
set RESOLVE_SCRIPT_API=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting
set RESOLVE_SCRIPT_LIB=C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll
```

macOS:

```bash
export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
```

Linux:

```bash
export RESOLVE_SCRIPT_API=/opt/resolve/Developer/Scripting
export RESOLVE_SCRIPT_LIB=/opt/resolve/libs/Fusion/fusionscript.so
```

The adapter loads `$RESOLVE_SCRIPT_API/Modules/DaVinciResolveScript.py` and calls
its `scriptapp("Resolve")`.

### 2. Enable external scripting in Resolve

Open `DaVinci Resolve > Preferences > System > General` (macOS) or
`Preferences > System > General`, and under **External Scripting** set it to
**Local** (or **Network** if you are driving a Resolve on another machine).

### 3. Serve

```bash
dcc-mcp-resolve serve
```

Do not pass `--pid` on this transport: the adapter process owns its own
lifetime, and Resolve may restart independently.

### If it does not connect

`doctor` distinguishes the three cases, because they have different fixes:

- `transport_error` naming `DaVinciResolveScript.py` — the scripting directory
  was not found. Fix `RESOLVE_SCRIPT_API`.
- `failure_stage: transport` with a message about **Studio** — you are on the
  free edition. Use Transport 2, or upgrade to Studio.
- `host_available: false` with no error — Resolve is simply not running, or
  external scripting is disabled in Preferences.

## Transport 2: in-process scripts

Use this on the free edition, or when you want to run inside the host. The
adapter becomes a script launched from Resolve's own Scripts menu, where Resolve
injects a `resolve` global.

### 1. Install the adapter into Resolve's script environment

The script must be importable by the interpreter Resolve uses for Python
scripting. Resolve ships its own interpreter (ResolvePython 3.14 in 21.1);
community practice clusters on 3.9–3.11. This package keeps
`requires-python = ">=3.7"`, and the bridge is imported lazily so a
version mismatch produces a clear `doctor` finding rather than an import crash.

### 2. Add the adapter as a script

1. Place the bootstrap script in a directory Resolve scans.
2. Open `Workspace > Scripts` in Resolve.
3. Launch the adapter script from that menu.

### 3. Serve

```bash
export DCC_MCP_RESOLVE_TRANSPORT=in_process
dcc-mcp-resolve serve --pid <resolve-pid>
```

`--pid` is required on this transport: the service's lifetime is bound to the
Resolve process.

## Verifying

`dcc-mcp-resolve doctor` reports, for the active transport:

- `transport` — which channel is in use.
- `host_version` / `host_available` — whether Resolve answered.
- `host_edition` — `studio` or `free`.
- `external_scripting_allowed` — whether this host should accept `external`.
- `host_version_supported` — whether that version sits on a supported line.
- `scripting_dirs_found` — which scripting directories exist on this machine.

## Uninstall

```bash
pip uninstall dcc-mcp-resolve
```

On the in-process transport, remove the script you added from Resolve's Scripts
directory. Keep any Python configuration that other Resolve scripts still use.

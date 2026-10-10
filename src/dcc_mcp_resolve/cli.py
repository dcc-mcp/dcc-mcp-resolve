"""CLI bootstrap: standalone external service or in-app script service."""

import argparse
import json
import os
import signal
import threading

from . import __version__


def build_parser():
    parser = argparse.ArgumentParser(description="DaVinci Resolve adapter for DCC-MCP")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("doctor", help="print a readiness report as JSON")

    serve = sub.add_parser("serve", help="run the MCP service")
    serve.add_argument("--port", type=int)
    serve.add_argument("--pid", type=int, help="Resolve host PID (in_process only)")
    serve.add_argument("--host-version", help="reported Resolve version")
    serve.add_argument(
        "--transport",
        choices=("in_process", "external"),
        help="override DCC_MCP_RESOLVE_TRANSPORT",
    )
    return parser


def _doctor():
    from .runtime import environment_report

    print(json.dumps(environment_report(), indent=2))
    return 0


def _serve(args, parser):
    from .transport import IN_PROCESS, TransportError, resolve_transport

    try:
        transport = resolve_transport(args.transport)
    except TransportError as exc:
        parser.error(str(exc))
        return 2

    if transport == IN_PROCESS and not args.pid:
        parser.error("--pid is required for the in_process transport")
        return 2
    if transport != IN_PROCESS and args.pid:
        parser.error("--pid is only valid for the in_process transport")
        return 2

    if args.transport:
        os.environ["DCC_MCP_RESOLVE_TRANSPORT"] = transport

    from .server import ResolveServer

    server = ResolveServer(
        port=args.port,
        dcc_pid=args.pid,
        dcc_version=args.host_version,
        transport=transport,
    )
    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    try:
        server.start()
        server.register_builtin_actions()
        print(
            json.dumps(
                {
                    "mcp_url": server.mcp_url,
                    "instance_id": server.instance_id,
                    "transport": transport,
                }
            ),
            flush=True,
        )
        while not stopped.wait(1):
            pass
    finally:
        server.stop()
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return _doctor()
    if args.command == "serve":
        return _serve(args, parser)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

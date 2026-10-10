"""Run the dcc-mcp repository contract against this repository.

Thin wrapper around the organisation checker in dcc-mcp/.github so contributors
can run the same gate locally that CI runs through the reusable workflow. It
clones the tooling only when a local checkout is not supplied.

    python scripts/check_repo_contract.py [--tooling PATH] [--profile strict]
"""

import argparse
import os
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLING_REPO = "https://github.com/dcc-mcp/.github.git"
CONTRACT = os.path.join("contract", "repo_contract.json")
CHECKER = os.path.join("scripts", "check_repo_contract.py")


def resolve_tooling(explicit):
    """Return a path to the .github checkout holding the checker and contract."""
    if explicit:
        return explicit
    env = os.environ.get("DCC_MCP_CONTRACT_TOOLING")
    if env:
        return env
    sibling = os.path.join(os.path.dirname(REPO_ROOT), ".github")
    if os.path.isfile(os.path.join(sibling, CHECKER)):
        return sibling
    return None


def clone_tooling():
    """Clone the org tooling to a temporary directory and return its path."""
    target = os.path.join(tempfile.mkdtemp(prefix="dcc-mcp-contract-"), ".github")
    subprocess.run(["git", "clone", "--depth", "1", TOOLING_REPO, target], check=True)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tooling", help="path to a dcc-mcp/.github checkout")
    parser.add_argument("--profile", default="baseline", choices=["baseline", "strict"])
    parser.add_argument("--fail-on", default="error", choices=["error", "warning", "none"])
    args = parser.parse_args(argv)

    tooling = resolve_tooling(args.tooling)
    if tooling is None:
        print("cloning %s for the contract tooling" % TOOLING_REPO, file=sys.stderr)
        tooling = clone_tooling()

    command = [
        sys.executable,
        os.path.join(tooling, CHECKER),
        "--root",
        REPO_ROOT,
        "--contract",
        os.path.join(tooling, CONTRACT),
        "--profile",
        args.profile,
        "--fail-on",
        args.fail_on,
        "--format",
        "text",
    ]
    return subprocess.run(command, cwd=tooling).returncode


if __name__ == "__main__":
    raise SystemExit(main())

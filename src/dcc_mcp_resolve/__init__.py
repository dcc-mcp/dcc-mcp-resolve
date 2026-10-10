"""DaVinci Resolve adapter; host discovery is lazy."""

__version__ = "0.1.1"  # x-release-please-version


def __getattr__(name):
    if name == "ResolveServer":
        from .server import ResolveServer

        return ResolveServer
    raise AttributeError(name)

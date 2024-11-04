import argparse
import sys
from pathlib import Path

import platformdirs

from .daemon import Daemon as Daemon
from .forks import (
    get_default_resolutions,
    get_env_resolutions,
    get_fork_resolution,
)


def main():
    supported_forks_resolutions = {}
    try:
        # First try to get the resolutions from the environment
        supported_forks_resolutions = get_env_resolutions()
    except Exception:
        pass
    if not supported_forks_resolutions:
        # If the environment does not have the resolutions, use the defaults
        supported_forks_resolutions = get_default_resolutions()
    supported_forks = "\n".join(supported_forks_resolutions.keys())
    epilog = "Supported Forks:\n" + supported_forks

    parser = argparse.ArgumentParser(
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("subcommand", type=str)
    parser.add_argument("--state.fork", dest="state_fork", type=str)
    parser.add_argument("--uds", type=str)
    parser.add_argument("--timeout", type=int)
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="ethereum-spec-evm-resolver 0.0.1",
    )

    (args, _) = parser.parse_known_args()

    Path(platformdirs.user_cache_dir("ethereum-spec-evm-resolver")).mkdir(
        parents=True, exist_ok=True
    )

    if args.subcommand in ["t8n", "b11r", "spawn-daemon"]:
        get_fork_resolution(args.state_fork).resolve(args.state_fork).add_to_path()
        if args.subcommand == "spawn-daemon":
            # Underscore to avoid clash with global variable
            from ethereum_spec_tools.evm_tools import Daemon as Daemon_

            sys.exit(Daemon_(args).run())
        else:
            from ethereum_spec_tools.evm_tools import main as main_

            sys.exit(main_())
    elif args.subcommand == "daemon":
        Daemon(args.uds).run()

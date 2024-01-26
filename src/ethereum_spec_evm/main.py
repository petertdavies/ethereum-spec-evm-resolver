import argparse
import json
import sys
from pathlib import Path
from shutil import rmtree

from filelock import FileLock
from git import Repo

fork_data = {
    "Cancun": {
        "url": "https://github.com/ethereum/execution-specs.git",
        "branch": "forks/cancun",
    }
}

for fork_name in [
    "Frontier",
    "Homestead",
    "EIP150",
    "EIP158",
    "Byzantium",
    "Constantinople",
    "Istanbul",
    "Berlin",
    "London",
    "Merge",
    "Shanghai",
]:
    fork_data[fork_name] = {
        "url": "https://github.com/ethereum/execution-specs.git",
        "branch": "master",
    }

data_dir = Path.home() / ".ethereum-spec-evm" / "fork-data"
config_file = Path.home() / ".ethereum-spec-evm" / "config.json"


def setup_data_dir():
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
    if not config_file.exists():
        with config_file.open("w") as fp:
            json.dump({"Frontier": fork_data["Frontier"]}, fp, indent=4)
            fp.write("\n")


def get_fork_data(fork):
    if config_file.exists():
        with config_file.open() as fp:
            config = json.load(fp)
            if fork in config:
                return config[fork]
    return fork_data[fork]


def download_fork(fork, data):
    fork_dir = data_dir / fork
    lock_file = data_dir / (fork + ".lock")
    loaded_file = data_dir / (fork + ".loaded")

    data_json_str = json.dumps(data)

    with FileLock(lock_file):
        try:
            if loaded_file.read_text() == data_json_str:
                return
        except FileNotFoundError:
            pass

        loaded_file.unlink(missing_ok=True)
        if fork_dir.exists():
            rmtree(fork_dir)

        if "commit" in data:
            repo = Repo.clone_from(
                data["url"],
                data_dir / fork,
                multi_options=["--single-branch", "--branch=" + data["branch"]],
            )
            repo.git.checkout(data["commit"])
        else:
            Repo.clone_from(
                data["url"],
                data_dir / fork,
                multi_options=["--depth=1", "--branch=" + data["branch"]],
            )

        rmtree(fork_dir / ".git")

        (data_dir / (fork + ".loaded")).write_text(data_json_str)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("subcommand", type=str)
    parser.add_argument("--state.fork", dest="state_fork", type=str)
    parser.add_argument(
        "-v", "--version", action="version", version="ethereum-spec-evm 0.0.1"
    )

    (args, _) = parser.parse_known_args()

    setup_data_dir()

    if args.subcommand in ["t8n", "b11r"]:
        download_fork(args.state_fork, fork_data[args.state_fork])

        sys.path[:0] = [str(data_dir / args.state_fork / "src")]

        from ethereum_spec_tools.evm_tools import main

        sys.exit(main())
    elif args.subcommand == "update":
        (data_dir / (args.state_fork + ".loaded")).unlink(missing_ok=True)
        download_fork(args.state_fork, fork_data[args.state_fork])

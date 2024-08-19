import argparse
import json
import subprocess
import sys
import socketserver
import time
import os
from typing import Optional, Tuple, Any, Union
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory
from subprocess import Popen
from threading import Thread
from platformdirs import user_runtime_dir
from socket import socket
from requests_unixsocket import Session

from filelock import FileLock
from git import Repo

default_fork_data = {
    "Prague": {
        "url": "https://github.com/ethereum/execution-specs.git",
        "branch": "forks/prague"
    }
}

for fork_name in [
    "Frontier",
    "Homestead",
    "EIP150",
    "EIP158",
    "Byzantium",
    "ConstantinopleFix",
    "Istanbul",
    "Berlin",
    "London",
    "Merge",
    "Shanghai",
    "Cancun",
]:
    default_fork_data[fork_name] = {
        "url": "https://github.com/ethereum/execution-specs.git",
        "branch": "master",
    }

data_dir = Path.home() / ".ethereum-spec-evm-resolver" / "fork-data"
config_file = Path.home() / ".ethereum-spec-evm-resolver" / "config.json"


def setup_data_dir():
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
    if not config_file.exists():
        with config_file.open("w") as fp:
            json.dump({"Frontier": default_fork_data["Frontier"]}, fp, indent=4)
            fp.write("\n")


def get_fork_data(fork):
    if config_file.exists():
        with config_file.open() as fp:
            config = json.load(fp)
            if fork in config:
                return config[fork]
    return default_fork_data[fork]


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


class _EvmToolHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        content_length = int(self.headers["Content-Length"])
        content_bytes = self.rfile.read(content_length)
        content = json.loads(content_bytes)

        fork = content['state']['fork']

        self.server.spawn_subserver(fork)

        socket_path = data_dir / (fork + "." + str(os.getpid()) + ".sock")
        replaced_str = str(socket_path).replace("/", "%2F")
        self.server_url = f"http+unix://{replaced_str}/"

        print(self.server_url)

        response = Session().post(self.server_url, json=content, timeout=60)

        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.end_headers()

        self.wfile.write(response.text.encode("utf-8"))




class _UnixSocketHttpServer(socketserver.UnixStreamServer):
    last_response: Optional[float] = None

    def __init__(self, *args, **kwargs):
        self.running_daemons = set()
        self.processes = []
        super().__init__(*args, **kwargs)

    def get_request(self) -> Tuple[Any, Any]:
        request, client_address = super().get_request()
        return request, ["local", 0]

    def finish_request(
            self, request: Union[socket, Tuple[bytes, socket]], client_address: Any
    ) -> None:
        try:
            super().finish_request(request, client_address)
        finally:
            self.last_response = time.monotonic()

    def check_timeout(self) -> None:
        while True:
            time.sleep(11.0)
            now = time.monotonic()
            last_response = self.last_response
            if last_response is None:
                self.last_response = now
            elif now - last_response > 60.0:
                self.shutdown()
                break

    def spawn_subserver(self, fork):
        print(fork)
        if fork not in self.running_daemons:
            download_fork(fork, get_fork_data(fork))

            self.processes.append(subprocess.Popen(
                args=[
                    sys.argv[0],
                    "spawn-daemon",
                    "--state.fork",
                    fork,
                    "--uds",
                    str(data_dir / (fork + "." + str(os.getpid()) + ".sock") ),
                    "--timeout=0",
                ]
            ))
            self.running_daemons.add(fork)
            time.sleep(1)


class Daemon_:
    """
    Converts HTTP requests into ethereum-spec-evm calls.
    """

    def __init__(self, uds) -> None:
        self.uds = uds

    def _run(self) -> int:
        try:
            os.remove(self.uds)
        except IOError:
            pass

        with _UnixSocketHttpServer(self.uds, _EvmToolHandler) as server:
            server.timeout = 7.0
            timer = Thread(target=server.check_timeout, daemon=True)
            timer.start()

            server.serve_forever()

        return 0

    def run(self) -> int:
        """
        Execute the tool.
        """
        return self._run()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("subcommand", type=str)
    parser.add_argument("--state.fork", dest="state_fork", type=str)
    parser.add_argument("--uds")
    parser.add_argument("--timeout", type=int)
    parser.add_argument(
        "-v", "--version", action="version", version="ethereum-spec-evm-resolver 0.0.1"
    )

    (args, _) = parser.parse_known_args()

    setup_data_dir()

    if args.subcommand in ["t8n", "b11r", "spawn-daemon"]:
        fork_data = get_fork_data(args.state_fork)
        if "path" in fork_data:
            sys.path[:0] = [str(Path(fork_data["path"]) / "src")]
        else:
            download_fork(args.state_fork, fork_data)
            sys.path[:0] = [str(data_dir / args.state_fork / "src")]

        if args.subcommand == "spawn-daemon":
            from ethereum_spec_tools.evm_tools import Daemon
            sys.exit(Daemon(args).run())
        else:
            from ethereum_spec_tools.evm_tools import main as main_
            sys.exit(main_())
    elif args.subcommand == "update":
        fork_data = get_fork_data(args.state_fork)
        (data_dir / (args.state_fork + ".loaded")).unlink(missing_ok=True)
        download_fork(args.state_fork, fork_data)
    elif args.subcommand == "daemon":
        print(Daemon_)
        Daemon_(args.uds).run()

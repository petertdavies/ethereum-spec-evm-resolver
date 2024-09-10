import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import rmtree
from typing import Dict, Optional, Union

import platformdirs
from filelock import FileLock
from git import Repo
from git.cmd import Git
from pydantic import (
    AliasChoices,
    AnyUrl,
    BaseModel,
    Field,
    PastDatetime,
    TypeAdapter,
    ValidationError,
)

RELOAD_CHECK_HOURS = 3


class ResolutionInfo(BaseModel):
    path: Path

    def add_to_path(self):
        sys.path[:0] = [str(self.path / "src")]


class LocalResolution(BaseModel):
    path: str

    def resolve(self, fork_name) -> ResolutionInfo:
        return ResolutionInfo(path=self.path)


class SameAsResolution(BaseModel):
    same_as: str

    def resolve(self, fork_name, hops_remaining=100):
        if hops_remaining == 0:
            raise Exception('"same_as" hop counter exceeded')
        resolution = get_fork_resolution(self.same_as)
        if isinstance(resolution, SameAsResolution):
            return resolution.resolve(fork_name, hops_remaining=hops_remaining - 1)
        else:
            return resolution.resolve(fork_name)


class GitResolution(BaseModel):
    git_url: AnyUrl
    branch: str = Field(AliasChoices("branch", "tag"))
    commit: Optional[str] = None

    def resolve(self, fork_name):
        data_dir = Path(platformdirs.user_cache_dir("ethereum-spec-evm-resolver"))
        fork_dir = data_dir / fork_name
        lock = FileLock(data_dir / (fork_name + ".lock"))
        info_file = data_dir / (fork_name + ".info")

        with lock:
            try:
                info = GitResolutionInfo.model_validate_json(info_file.read_text())
                if self == info.resolution:
                    if self.commit is not None or datetime.now(
                        tz=timezone.utc
                    ) - info.timestamp < timedelta(hours=RELOAD_CHECK_HOURS):
                        return ResolutionInfo(path=fork_dir)
                if self.commit is None:
                    if self.get_remote_head() == info.head:
                        return ResolutionInfo(path=fork_dir)
            except (FileNotFoundError, ValidationError):
                pass
            if fork_dir.exists():
                rmtree(fork_dir)
            if self.commit is None:
                repo = Repo.clone_from(
                    str(self.git_url),
                    fork_dir,
                    multi_options=["--depth=1", "--branch=" + self.branch],
                )
            else:
                repo = Repo.clone_from(
                    str(self.git_url),
                    fork_dir,
                    multi_options=[
                        "--single-branch",
                        "--branch=" + self.branch,
                    ],
                )
                repo.git.checkout(self.commit)
            info_file.write_text(
                GitResolutionInfo(
                    resolution=self,
                    timestamp=datetime.now(tz=timezone.utc),
                    head=repo.head.commit.hexsha,
                ).model_dump_json()
            )
            rmtree(fork_dir / ".git")
            return ResolutionInfo(path=fork_dir)

    def get_remote_head(self) -> str:
        git = Git()
        ans = git.ls_remote(str(self.git_url), self.branch)
        assert "\n" not in ans
        commit, remote_ref = ans.split("\t")
        return commit


class GitResolutionInfo(BaseModel):
    resolution: GitResolution
    timestamp: PastDatetime
    head: str


Resolution = Union[LocalResolution, SameAsResolution, GitResolution]


def get_default_resolutions() -> Dict[str, Resolution]:
    resolutions = {
        "EELSMaster": {
            "git_url": "https://github.com/ethereum/execution-specs.git",
            "branch": "master",
        },
        "Prague": {
            "git_url": "https://github.com/ethereum/execution-specs.git",
            "branch": "forks/prague",
        },
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
        resolutions[fork_name] = {"same_as": "EELSMaster"}
    return TypeAdapter(Dict[str, Resolution]).validate_python(resolutions)


def get_env_resolutions() -> Dict[str, Resolution]:
    resolutions_string = os.environ.get("EELS_RESOLUTIONS")
    resolutions_file = os.environ.get("EELS_RESOLUTIONS_FILE")
    if resolutions_string is not None and resolutions_file is not None:
        raise Exception(
            "Only one of EELS_RESOLUTIONS and "
            + "EELS_RESOLUTIONS_FILE allowed in env vars"
        )
    elif resolutions_string is not None:
        return TypeAdapter(Dict[str, Resolution]).validate_json(resolutions_string)
    elif resolutions_file is not None:
        return TypeAdapter(Dict[str, Resolution]).validate_json(
            Path(resolutions_file).read_text()
        )
    else:
        return {}


default_resolutions = get_default_resolutions()
env_resolutions = get_env_resolutions()

def get_fork_resolution(fork_name: str) -> Resolution:
    if fork_name in env_resolutions:
        return env_resolutions[fork_name]
    elif fork_name in default_resolutions:
        return default_resolutions[fork_name]
    else:
        raise Exception(f"Unable to resolve fork: {fork_name}")

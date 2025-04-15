# Ethereum Spec EVM Resolver

This tool implements the `evm` tool for EELS. It is capable of handling
requests for different EVM forks even when those forks are implemented by
different versions of EELS hosted in different places. Forks of EELS are
downloaded on demand.

EELS resolver supports two modes of operation:

In direct mode (e.g. `ethereum-spec-evm-resolver t8n`), EELS resolver
will simply pass the entire request onto the relevant EELS fork based on the
`--state.fork` command line option.

In daemon mode, EELS resolver will spin up a daemon which will listen for
requests on the Unix domain socket using the `--uds` option. That daemon will
then manage a fleet of sub-daemons to handle incoming requests.

## Adding custom forks

Support for custom forks can be specified using json config. The json may be
placed directly in the environment variable `$EELS_RESOLUTIONS` or in the file
at `$EELS_RESOLUTIONS_FILE`.

### Git resolutions

Git resolutions accept the following keys:

`git_url`
: The url of the git repo

`branch`/`tag`
: The branch or tag to use

`commit` (optional)
: The specific commit to use (must be an ancestor of
branch head)

### Local resolutions

Local resolutions only have the `path` key.

`path`
: path to the project root of an `execution-specs` repository (not to the fork sub-folder).

### Same as resolutions

Same as resolutions avoid redundancy when one repo contains multiple forks.

`same_as`
: The fork with that resolves to the same repo.

## Example config

```json
{
    "EELSMaster": {
        "git_url": "https://github.com/ethereum/execution-specs.git",
        "branch": "master"
    },
    "Frontier": {
        "same_as": "EELSMaster"
    },
    "LocalFork": {
        "path": "/path/to/forked/execution-specs/"
    }    
}
```

## Example `EELS_RESOLUTIONS` Usage

Setting resolutions via `EELS_RESOLUTIONS` will take precedent over an resolutions file, `eels_resolutions.json`:

Fish:

```shell
set -x EELS_RESOLUTIONS '{"Prague": {"path": "/path/to/forked/execution-specs/"}}'
```

Bash:

```bash
export EELS_RESOLUTIONS='{"Prague": {"path": "/path/to/forked/execution-specs/"}}'
```

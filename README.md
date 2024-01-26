# EELS evm forwarding tool

This tool implements the `evm` tool for EELS. The command line options will be
forwarded to EELS based on the `--state.fork` option. All options are passed
to EELS verbatim.

Once downloaded the local copy of EELS for each fork will not be updated, but
a manual update of a fork can be forced using `update`.

# Custom forks

A custom fork can be added to this tool by editing the config file in
`~/.ethereum-spec-evm/config.json`. The following keys are accepted:
* `url`: The url of the git repository containing the fork of EELS.
* `branch`: The branch (or tag) of the fork.
* `commit`: The particular commit to checkout, it must be an ancestor of
`branch`.

## Example config
```commandline
{
    "Frontier": {
        "url": "https://github.com/ethereum/execution-specs.git",
        "branch": "master"
    }
}
```


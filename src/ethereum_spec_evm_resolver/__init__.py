from importlib.metadata import version

__version__ = version("ethereum_spec_evm_resolver")

from ethereum_spec_evm_resolver.daemon import Daemon
from ethereum_spec_evm_resolver.forks import (
    Resolution,
)


__all__ = [
    "__version__",
    "Daemon",
    "Resolution",
]

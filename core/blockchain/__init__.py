"""
core.blockchain — Blockchain integration for cryptocurrency inheritance.

Provides:
- Secure wallet management for cryptocurrency assets
- Multi-signature wallet support
- Transaction monitoring and verification
- Inheritance trigger mechanisms
"""

from core.blockchain.constants import (
    BLOCK_EXPLORERS,
    CONFIRMATION_BLOCKS,
    DEFAULT_NETWORK,
    GAS_PRICE_MULTIPLIER,
    INHERITANCE_TIMEOUT_DAYS,
    RPC_ENDPOINTS,
    SUPPORTED_NETWORKS,
)

from core.blockchain.manager import (
    BlockchainManager,
    get_blockchain_manager,
)

from core.blockchain.types import (
    BlockchainConfig,
    InheritanceRule,
    InheritanceTrigger,
    Transaction,
    TransactionStatus,
    WalletConfig,
    WalletType,
)

__all__ = [
    # Constants
    "BLOCK_EXPLORERS",
    "CONFIRMATION_BLOCKS",
    "DEFAULT_NETWORK",
    "GAS_PRICE_MULTIPLIER",
    "INHERITANCE_TIMEOUT_DAYS",
    "RPC_ENDPOINTS",
    "SUPPORTED_NETWORKS",
    # Manager
    "BlockchainManager",
    "get_blockchain_manager",
    # Types
    "BlockchainConfig",
    "InheritanceRule",
    "InheritanceTrigger",
    "Transaction",
    "TransactionStatus",
    "WalletConfig",
    "WalletType",
]

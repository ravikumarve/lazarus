"""
Lazarus Core — encryption, storage, config management, license validation, and blockchain.
"""

from core.blockchain import (
    BlockchainManager,
    BlockchainConfig,
    WalletConfig,
    Transaction,
    InheritanceRule,
    WalletType,
    TransactionStatus,
    InheritanceTrigger,
    get_blockchain_manager,
)

from core.hardware_wallet import (
    HardwareWalletManager,
    HardwareWalletConfig,
    HardwareWalletType,
    HardwareWalletStatus,
    get_hardware_wallet_manager,
)

from core.smart_contract import (
    SmartContractManager,
    SmartContractConfig,
    ContractConfig,
    ContractType,
    ContractStatus,
    ContractDeployment,
)

__all__ = [
    # Blockchain
    "BlockchainManager",
    "BlockchainConfig",
    "WalletConfig",
    "Transaction",
    "InheritanceRule",
    "WalletType",
    "TransactionStatus",
    "InheritanceTrigger",
    "get_blockchain_manager",
    # Hardware Wallet
    "HardwareWalletManager",
    "HardwareWalletConfig",
    "HardwareWalletType",
    "HardwareWalletStatus",
    "get_hardware_wallet_manager",
    # Smart Contract
    "SmartContractManager",
    "SmartContractConfig",
    "ContractConfig",
    "ContractType",
    "ContractStatus",
    "ContractDeployment",
]

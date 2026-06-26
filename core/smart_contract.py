from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional

try:
    from eth_account import Account
    from eth_utils import to_checksum_address, to_hex
    from web3 import Web3
    from web3.exceptions import ContractLogicError, TransactionNotFound
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    Web3 = None
    Account = None
    TransactionNotFound = Exception
    ContractLogicError = Exception
    to_checksum_address = lambda x: x
    to_hex = lambda x: x

from core.blockchain import BlockchainConfig, BlockchainManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_GAS_LIMIT = 200000
DEFAULT_GAS_PRICE_MULTIPLIER = 1.2
CONTRACT_DEPLOYMENT_TIMEOUT = 600  # 10 minutes
INHERITANCE_EXECUTION_TIMEOUT = 300  # 5 minutes

# Smart contract ABI templates
INHERITANCE_CONTRACT_ABI = [
    {
        "inputs": [
            {"name": "_beneficiary", "type": "address"},
            {"name": "_checkinPeriod", "type": "uint256"},
            {"name": "_gracePeriod", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "beneficiary", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"}
        ],
        "name": "InheritanceExecuted",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"}
        ],
        "name": "CheckinReceived",
        "type": "event"
    },
    {
        "inputs": [],
        "name": "checkin",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "executeInheritance",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "beneficiary",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "lastCheckin",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "checkinPeriod",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "gracePeriod",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "canExecuteInheritance",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getBalance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ContractStatus(Enum):
    """Status of smart contracts"""
    DEPLOYING = "deploying"
    ACTIVE = "active"
    PAUSED = "paused"
    EXECUTED = "executed"
    FAILED = "failed"


class ContractType(Enum):
    """Types of smart contracts"""
    INHERITANCE = "inheritance"
    MULTISIG = "multisig"
    TIMELOCK = "timelock"
    ESCROW = "escrow"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ContractConfig:
    """Configuration for a smart contract"""
    contract_address: str
    contract_type: ContractType
    network: str
    owner_address: str
    beneficiary_address: Optional[str] = None
    checkin_period: Optional[int] = None  # in seconds
    grace_period: Optional[int] = None  # in seconds
    created_at: Optional[datetime] = None
    status: ContractStatus = ContractStatus.ACTIVE
    balance: Optional[Decimal] = None
    last_checkin: Optional[datetime] = None


@dataclass
class ContractDeployment:
    """Smart contract deployment information"""
    contract_address: str
    transaction_hash: str
    block_number: int
    gas_used: int
    gas_price: int
    deployment_cost: Decimal
    timestamp: datetime


@dataclass
class SmartContractConfig:
    """Configuration for smart contract integration"""
    network: str = "mainnet"
    gas_limit: int = DEFAULT_GAS_LIMIT
    gas_price_multiplier: float = DEFAULT_GAS_PRICE_MULTIPLIER
    deployment_timeout: int = CONTRACT_DEPLOYMENT_TIMEOUT
    execution_timeout: int = INHERITANCE_EXECUTION_TIMEOUT
    enable_auto_checkin: bool = False
    checkin_interval: int = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Smart Contract Manager
# ---------------------------------------------------------------------------

class SmartContractManager:
    """
    Manager for smart contract operations and automated inheritance.

    This class provides:
    - Smart contract deployment
    - Contract interaction and monitoring
    - Automated inheritance execution
    - Event monitoring and logging
    - Gas optimization
    """

    def __init__(
        self,
        blockchain_manager: Optional[BlockchainManager] = None,
        config: Optional[SmartContractConfig] = None
    ):
        """
        Initialize smart contract manager.

        Args:
            blockchain_manager: Blockchain manager instance
            config: Smart contract configuration
        """
        if not WEB3_AVAILABLE:
            raise ImportError(
                "Web3.py is required for smart contract functionality. "
                "Install with: pip install web3"
            )

        self.config = config or SmartContractConfig()
        self._logger = logging.getLogger("lazarus.smart_contract")

        # Initialize blockchain manager
        self._blockchain_manager = blockchain_manager or BlockchainManager(
            BlockchainConfig(network=self.config.network)
        )

        # Get Web3 instance
        self._w3 = self._blockchain_manager._w3

        # Load contracts from database
        self._contracts: Dict[str, ContractConfig] = {}
        self._load_contracts()

        self._logger.info(f"Smart contract manager initialized: {self.config.network}")

    def _load_contracts(self) -> None:
        """Load contracts from database"""
        try:
            # In a real implementation, this would load from database
            self._logger.info("Contracts loaded from database")
        except Exception as e:
            self._logger.error(f"Failed to load contracts: {e}")

    # ---------------------------------------------------------------------------
    # Contract Deployment
    # ---------------------------------------------------------------------------

    def _build_constructor_tx(self, contract, beneficiary_address: str, checkin_period: int, grace_period: int, deployer_address: str) -> dict:
        """Build the constructor transaction for contract deployment."""
        return contract.constructor(
            to_checksum_address(beneficiary_address),
            checkin_period,
            grace_period
        ).build_transaction({
            'from': deployer_address,
            'gas': self.config.gas_limit,
            'gasPrice': int(self._w3.eth.gas_price * self.config.gas_price_multiplier),
            'nonce': self._w3.eth.get_transaction_count(deployer_address),
            'chainId': self._w3.eth.chain_id
        })

    def _deploy_and_wait(self, constructor_tx: dict, private_key: str) -> tuple:
        """Sign, send, and wait for contract deployment. Returns (tx_hash, receipt)."""
        signed_tx = self._w3.eth.account.sign_transaction(constructor_tx, private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        self._logger.info(f"Contract deployment transaction sent: {tx_hash.hex()}")
        receipt = self._w3.eth.wait_for_transaction_receipt(
            tx_hash, timeout=self.config.deployment_timeout
        )
        return tx_hash, receipt

    def _record_deployment(self, receipt, tx_hash, deployer_address: str, beneficiary_address: str, checkin_period: int, grace_period: int) -> ContractDeployment:
        """Record deployment results and save contract configuration."""
        contract_address = receipt['contractAddress']
        deployment_cost = Decimal(str(self._w3.from_wei(
            receipt['gasUsed'] * receipt['effectiveGasPrice'], 'ether'
        )))
        deployment = ContractDeployment(
            contract_address=contract_address,
            transaction_hash=tx_hash.hex(),
            block_number=receipt['blockNumber'],
            gas_used=receipt['gasUsed'],
            gas_price=receipt['effectiveGasPrice'],
            deployment_cost=deployment_cost,
            timestamp=datetime.now(UTC)
        )
        contract_config = ContractConfig(
            contract_address=contract_address,
            contract_type=ContractType.INHERITANCE,
            network=self.config.network,
            owner_address=deployer_address,
            beneficiary_address=beneficiary_address,
            checkin_period=checkin_period,
            grace_period=grace_period,
            created_at=datetime.now(UTC),
            status=ContractStatus.ACTIVE
        )
        self._contracts[contract_address] = contract_config
        self._save_contract(contract_config)
        self._logger.info(
            f"Inheritance contract deployed: {contract_address} (cost: {deployment_cost} ETH)"
        )
        return deployment

    def deploy_inheritance_contract(
        self,
        beneficiary_address: str,
        checkin_period: int = 86400,  # 24 hours
        grace_period: int = 2592000,  # 30 days
        private_key: Optional[str] = None
    ) -> Optional[ContractDeployment]:
        """
        Deploy an inheritance smart contract.

        Args:
            beneficiary_address: Beneficiary wallet address
            checkin_period: Time between required check-ins (seconds)
            grace_period: Grace period before inheritance executes (seconds)
            private_key: Deployer's private key

        Returns:
            Contract deployment information or None
        """
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        if not private_key:
            self._logger.error("Private key required for contract deployment")
            return None

        try:
            deployer_address = to_checksum_address(Account.from_key(private_key).address)
            if not self._blockchain_manager.validate_address(beneficiary_address):
                self._logger.error(f"Invalid beneficiary address: {beneficiary_address}")
                return None

            contract = self._w3.eth.contract(
                abi=INHERITANCE_CONTRACT_ABI,
                bytecode=self._get_inheritance_contract_bytecode()
            )

            constructor_tx = self._build_constructor_tx(
                contract, beneficiary_address, checkin_period, grace_period, deployer_address
            )
            tx_hash, receipt = self._deploy_and_wait(constructor_tx, private_key)
            return self._record_deployment(
                receipt, tx_hash, deployer_address, beneficiary_address,
                checkin_period, grace_period
            )

        except Exception as e:
            self._logger.error(f"Failed to deploy inheritance contract: {e}")
            return None

    def _get_inheritance_contract_bytecode(self) -> str:
        """
        Get inheritance contract bytecode.

        Returns:
            Contract bytecode
        """
        # In a real implementation, this would load from compiled contract files
        # For now, return a placeholder

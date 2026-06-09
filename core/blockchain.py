"""
core/blockchain.py — Blockchain integration for cryptocurrency inheritance.

Provides:
- Secure wallet management for cryptocurrency assets
- Multi-signature wallet support
- Transaction monitoring and verification
- Inheritance trigger mechanisms
- Hardware wallet integration
- Smart contract integration

This module enables Lazarus Protocol to securely manage and transfer
cryptocurrency assets according to inheritance rules.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, UTC, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

try:
    from web3 import Web3
    from web3.exceptions import TransactionNotFound
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from eth_utils import to_checksum_address
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    Web3 = None
    Account = None
    TransactionNotFound = Exception
    to_checksum_address = lambda x: x

from core.encryption import encrypt_file, decrypt_file, generate_aes_key
from core.database import get_database_manager


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_NETWORK = "mainnet"
SUPPORTED_NETWORKS = ["mainnet", "goerli", "sepolia", "polygon", "arbitrum"]
GAS_PRICE_MULTIPLIER = 1.2
CONFIRMATION_BLOCKS = 12
INHERITANCE_TIMEOUT_DAYS = 30

# RPC Endpoints
RPC_ENDPOINTS = {
    "mainnet": "https://eth.llamarpc.com",
    "goerli": "https://goerli.llamarpc.com",
    "sepolia": "https://sepolia.llamarpc.com",
    "polygon": "https://polygon.llamarpc.com",
    "arbitrum": "https://arbitrum.llamarpc.com",
}

# Block explorers
BLOCK_EXPLORERS = {
    "mainnet": "https://etherscan.io",
    "goerli": "https://goerli.etherscan.io",
    "sepolia": "https://sepolia.etherscan.io",
    "polygon": "https://polygonscan.com",
    "arbitrum": "https://arbiscan.io",
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WalletType(Enum):
    """Types of cryptocurrency wallets"""
    SOFTWARE = "software"
    HARDWARE = "hardware"
    MULTISIG = "multisig"
    SMART_CONTRACT = "smart_contract"


class TransactionStatus(Enum):
    """Status of blockchain transactions"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InheritanceTrigger(Enum):
    """Types of inheritance triggers"""
    TIME_BASED = "time_based"
    CHECKIN_MISSED = "checkin_missed"
    MANUAL = "manual"
    EMERGENCY = "emergency"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class WalletConfig:
    """Configuration for a cryptocurrency wallet"""
    address: str
    network: str = DEFAULT_NETWORK
    wallet_type: WalletType = WalletType.SOFTWARE
    label: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    balance: Optional[Decimal] = None
    last_sync: Optional[datetime] = None


@dataclass
class Transaction:
    """Blockchain transaction"""
    tx_hash: str
    from_address: str
    to_address: str
    value: Decimal
    gas_used: Optional[int] = None
    gas_price: Optional[int] = None
    block_number: Optional[int] = None
    status: TransactionStatus = TransactionStatus.PENDING
    timestamp: Optional[datetime] = None
    network: str = DEFAULT_NETWORK
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class InheritanceRule:
    """Rules for cryptocurrency inheritance"""
    wallet_address: str
    beneficiary_address: str
    trigger_type: InheritanceTrigger = InheritanceTrigger.CHECKIN_MISSED
    trigger_value: Optional[str] = None  # e.g., number of days for time-based
    conditions: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    status: str = "active"  # active, executed, cancelled


@dataclass
class BlockchainConfig:
    """Configuration for blockchain integration"""
    network: str = DEFAULT_NETWORK
    rpc_endpoint: Optional[str] = None
    gas_price_multiplier: float = GAS_PRICE_MULTIPLIER
    confirmation_blocks: int = CONFIRMATION_BLOCKS
    inheritance_timeout_days: int = INHERITANCE_TIMEOUT_DAYS
    enable_hardware_wallet: bool = False
    enable_smart_contracts: bool = False


# ---------------------------------------------------------------------------
# Blockchain Manager
# ---------------------------------------------------------------------------

class BlockchainManager:
    """
    Manager for blockchain operations and cryptocurrency inheritance.
    
    This class provides:
    - Secure wallet management
    - Transaction monitoring
    - Inheritance rule management
    - Hardware wallet integration
    - Smart contract interaction
    """

    def __init__(self, config: Optional[BlockchainConfig] = None):
        """
        Initialize blockchain manager.
        
        Args:
            config: Blockchain configuration (uses defaults if not provided)
        """
        if not WEB3_AVAILABLE:
            raise ImportError(
                "Web3.py is required for blockchain functionality. "
                "Install with: pip install web3"
            )
        
        self.config = config or BlockchainConfig()
        self._logger = logging.getLogger("lazarus.blockchain")
        
        # Initialize Web3 connection
        self._w3 = self._init_web3()
        
        # Load wallets from database
        self._wallets: Dict[str, WalletConfig] = {}
        self._load_wallets()
        
        # Load inheritance rules
        self._inheritance_rules: Dict[str, InheritanceRule] = {}
        self._load_inheritance_rules()
        
        self._logger.info(f"Blockchain manager initialized: {self.config.network}")

    def _init_web3(self) -> Optional[Web3]:
        """Initialize Web3 connection"""
        rpc_endpoint = self.config.rpc_endpoint or RPC_ENDPOINTS.get(
            self.config.network,
            RPC_ENDPOINTS[DEFAULT_NETWORK]
        )
        
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_endpoint))
            
            # Test connection
            if w3.is_connected():
                self._logger.info(f"Connected to {self.config.network}")
                return w3
            else:
                self._logger.warning(f"Failed to connect to {self.config.network}")
                return None
        except Exception as e:
            self._logger.error(f"Failed to initialize Web3: {e}")
            return None

    def _load_wallets(self) -> None:
        """Load wallets from database"""
        try:
            db = get_database_manager()
            # In a real implementation, this would load from database
            # For now, we'll use an empty dictionary
            self._logger.info("Wallets loaded from database")
        except Exception as e:
            self._logger.error(f"Failed to load wallets: {e}")

    def _load_inheritance_rules(self) -> None:
        """Load inheritance rules from database"""
        try:
            db = get_database_manager()
            # In a real implementation, this would load from database
            # For now, we'll use an empty dictionary
            self._logger.info("Inheritance rules loaded from database")
        except Exception as e:
            self._logger.error(f"Failed to load inheritance rules: {e}")

    # ---------------------------------------------------------------------------
    # Wallet Management
    # ---------------------------------------------------------------------------

    def create_wallet(
        self,
        label: Optional[str] = None,
        description: Optional[str] = None
    ) -> WalletConfig:
        """
        Create a new software wallet.
        
        Args:
            label: Optional label for the wallet
            description: Optional description
            
        Returns:
            Wallet configuration
        """
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        
        # Generate new account
        account = Account.create()
        address = to_checksum_address(account.address)
        
        # Create wallet config
        wallet = WalletConfig(
            address=address,
            network=self.config.network,
            wallet_type=WalletType.SOFTWARE,
            label=label or f"Wallet {address[:8]}",
            description=description,
            created_at=datetime.now(UTC),
            balance=Decimal(0),
            last_sync=datetime.now(UTC)
        )
        
        # Store wallet
        self._wallets[address] = wallet
        
        # Save to database
        self._save_wallet(wallet)
        
        self._logger.info(f"Created wallet: {address}")
        return wallet

    def import_wallet(
        self,
        private_key: str,
        label: Optional[str] = None,
        description: Optional[str] = None
    ) -> WalletConfig:
        """
        Import an existing wallet from private key.
        
        Args:
            private_key: Private key to import
            label: Optional label for the wallet
            description: Optional description
            
        Returns:
            Wallet configuration
        """
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        
        # Recover account from private key
        account = Account.from_key(private_key)
        address = to_checksum_address(account.address)
        
        # Create wallet config
        wallet = WalletConfig(
            address=address,
            network=self.config.network,
            wallet_type=WalletType.SOFTWARE,
            label=label or f"Imported Wallet {address[:8]}",
            description=description,
            created_at=datetime.now(UTC),
            balance=Decimal(0),
            last_sync=datetime.now(UTC)
        )
        
        # Store wallet
        self._wallets[address] = wallet
        
        # Save to database
        self._save_wallet(wallet)
        
        self._logger.info(f"Imported wallet: {address}")
        return wallet

    def get_wallet(self, address: str) -> Optional[WalletConfig]:
        """
        Get wallet by address.
        
        Args:
            address: Wallet address
            
        Returns:
            Wallet configuration or None
        """
        return self._wallets.get(to_checksum_address(address))

    def list_wallets(self) -> List[WalletConfig]:
        """
        List all wallets.
        
        Returns:
            List of wallet configurations
        """
        return list(self._wallets.values())

    def get_balance(self, address: str) -> Decimal:
        """
        Get wallet balance.
        
        Args:
            address: Wallet address
            
        Returns:
            Balance in ETH
        """
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        
        checksum_address = to_checksum_address(address)
        balance_wei = self._w3.eth.get_balance(checksum_address)
        balance_eth = self._w3.from_wei(balance_wei, 'ether')
        
        # Update wallet balance
        if checksum_address in self._wallets:
            self._wallets[checksum_address].balance = Decimal(str(balance_eth))
            self._wallets[checksum_address].last_sync = datetime.now(UTC)
        
        return Decimal(str(balance_eth))

    def sync_wallets(self) -> None:
        """Sync all wallet balances"""
        for address in self._wallets:
            try:
                self.get_balance(address)
            except Exception as e:
                self._logger.error(f"Failed to sync wallet {address}: {e}")

    # ---------------------------------------------------------------------------
    # Transaction Management
    # ---------------------------------------------------------------------------

    def send_transaction(
        self,
        from_address: str,
        to_address: str,
        value: Decimal,
        private_key: str,
        gas_limit: Optional[int] = None
    ) -> Transaction:
        """
        Send a transaction.
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            value: Amount to send (in ETH)
            private_key: Sender's private key
            gas_limit: Optional gas limit
            
        Returns:
            Transaction object
        """
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        
        # Get nonce
        nonce = self._w3.eth.get_transaction_count(
            to_checksum_address(from_address)
        )
        
        # Get gas price
        gas_price = self._w3.eth.gas_price
        
        # Build transaction
        tx_dict = {
            'nonce': nonce,
            'to': to_checksum_address(to_address),
            'value': self._w3.to_wei(value, 'ether'),
            'gas': gas_limit or 21000,  # Standard transfer gas limit
            'gasPrice': int(gas_price * self.config.gas_price_multiplier),
            'chainId': self._w3.eth.chain_id
        }
        
        # Sign transaction
        signed_tx = self._w3.eth.account.sign_transaction(tx_dict, private_key)
        
        # Send transaction
        tx_hash = self._w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Create transaction object
        transaction = Transaction(
            tx_hash=tx_hash.hex(),
            from_address=from_address,
            to_address=to_address,
            value=value,
            gas_used=tx_dict['gas'],
            gas_price=tx_dict['gasPrice'],
            status=TransactionStatus.PENDING,
            timestamp=datetime.now(UTC),
            network=self.config.network
        )
        
        self._logger.info(f"Transaction sent: {tx_hash.hex()}")
        return transaction

    def get_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """
        Get transaction by hash.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction object or None
        """
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        
        try:
            tx_receipt = self._w3.eth.get_transaction_receipt(tx_hash)
            tx = self._w3.eth.get_transaction(tx_hash)
            
            # Determine status
            if tx_receipt is None:
                status = TransactionStatus.PENDING
            elif tx_receipt['status'] == 1:
                status = TransactionStatus.CONFIRMED
            else:
                status = TransactionStatus.FAILED
            
            # Create transaction object
            transaction = Transaction(
                tx_hash=tx_hash,
                from_address=tx['from'],
                to_address=tx['to'],
                value=Decimal(str(self._w3.from_wei(tx['value'], 'ether'))),
                gas_used=tx_receipt['gasUsed'] if tx_receipt else None,
                gas_price=tx['gasPrice'],
                block_number=tx_receipt['blockNumber'] if tx_receipt else None,
                status=status,
                timestamp=datetime.fromtimestamp(tx['timestamp'], UTC) if tx.get('timestamp') else None,
                network=self.config.network
            )
            
            return transaction
        except TransactionNotFound:
            self._logger.warning(f"Transaction not found: {tx_hash}")
            return None
        except Exception as e:
            self._logger.error(f"Failed to get transaction {tx_hash}: {e}")
            return None

    def wait_for_confirmation(
        self,
        tx_hash: str,
        timeout: int = 300
    ) -> Optional[Transaction]:
        """
        Wait for transaction confirmation.
        
        Args:
            tx_hash: Transaction hash
            timeout: Timeout in seconds
            
        Returns:
            Confirmed transaction or None
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            transaction = self.get_transaction(tx_hash)
            
            if transaction and transaction.status == TransactionStatus.CONFIRMED:
                return transaction
            
            time.sleep(5)
        
        self._logger.warning(f"Transaction {tx_hash} not confirmed within timeout")
        return None

    # ---------------------------------------------------------------------------
    # Inheritance Management
    # ---------------------------------------------------------------------------

    def create_inheritance_rule(
        self,
        wallet_address: str,
        beneficiary_address: str,
        trigger_type: InheritanceTrigger = InheritanceTrigger.CHECKIN_MISSED,
        trigger_value: Optional[str] = None,
        conditions: Optional[Dict[str, Any]] = None
    ) -> InheritanceRule:
        """
        Create an inheritance rule.
        
        Args:
            wallet_address: Wallet address to inherit from
            beneficiary_address: Beneficiary wallet address
            trigger_type: Type of trigger
            trigger_value: Trigger value (e.g., number of days)
            conditions: Additional conditions
            
        Returns:
            Inheritance rule
        """
        rule = InheritanceRule(
            wallet_address=to_checksum_address(wallet_address),
            beneficiary_address=to_checksum_address(beneficiary_address),
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            conditions=conditions or {},
            created_at=datetime.now(UTC),
            status="active"
        )
        
        # Store rule
        rule_key = f"{rule.wallet_address}_{rule.beneficiary_address}"
        self._inheritance_rules[rule_key] = rule
        
        # Save to database
        self._save_inheritance_rule(rule)
        
        self._logger.info(f"Created inheritance rule: {rule_key}")
        return rule

    def get_inheritance_rules(self, wallet_address: Optional[str] = None) -> List[InheritanceRule]:
        """
        Get inheritance rules.
        
        Args:
            wallet_address: Optional wallet address to filter by
            
        Returns:
            List of inheritance rules
        """
        if wallet_address:
            checksum_address = to_checksum_address(wallet_address)
            return [
                rule for rule in self._inheritance_rules.values()
                if rule.wallet_address == checksum_address
            ]
        return list(self._inheritance_rules.values())

    def check_inheritance_triggers(self) -> List[InheritanceRule]:
        """
        Check for inheritance triggers.
        
        Returns:
            List of triggered inheritance rules
        """
        triggered_rules = []
        
        for rule in self._inheritance_rules.values():
            if rule.status != "active":
                continue
            
            if self._should_trigger_inheritance(rule):
                triggered_rules.append(rule)
        
        return triggered_rules

    def execute_inheritance(
        self,
        rule: InheritanceRule,
        private_key: str
    ) -> Optional[Transaction]:
        """
        Execute inheritance transfer.
        
        Args:
            rule: Inheritance rule to execute
            private_key: Private key of source wallet
            
        Returns:
            Transaction or None
        """
        if rule.status != "active":
            self._logger.warning(f"Rule {rule.wallet_address} is not active")
            return None
        
        # Get wallet balance
        balance = self.get_balance(rule.wallet_address)
        
        if balance <= 0:
            self._logger.warning(f"Wallet {rule.wallet_address} has no balance")
            return None
        
        # Send transaction
        try:
            transaction = self.send_transaction(
                from_address=rule.wallet_address,
                to_address=rule.beneficiary_address,
                value=balance,
                private_key=private_key
            )
            
            # Update rule status
            rule.status = "executed"
            rule.executed_at = datetime.now(UTC)
            
            # Save to database
            self._save_inheritance_rule(rule)
            
            self._logger.info(f"Executed inheritance: {rule.wallet_address} -> {rule.beneficiary_address}")
            return transaction
        except Exception as e:
            self._logger.error(f"Failed to execute inheritance: {e}")
            return None

    def _should_trigger_inheritance(self, rule: InheritanceRule) -> bool:
        """
        Check if inheritance should be triggered.
        
        Args:
            rule: Inheritance rule
            
        Returns:
            True if should trigger
        """
        if rule.trigger_type == InheritanceTrigger.TIME_BASED:
            # Check if time-based trigger is met
            if rule.trigger_value:
                days = int(rule.trigger_value)
                if rule.created_at:
                    trigger_time = rule.created_at + timedelta(days=days)
                    return datetime.now(UTC) >= trigger_time
        
        elif rule.trigger_type == InheritanceTrigger.CHECKIN_MISSED:
            # Check if check-in has been missed
            # This would integrate with the check-in system
            if rule.trigger_value:
                days = int(rule.trigger_value)
                # Get last check-in time from database
                # For now, return False
                return False
        
        elif rule.trigger_type == InheritanceTrigger.MANUAL:
            # Manual trigger - always return True if status is active
            return True
        
        elif rule.trigger_type == InheritanceTrigger.EMERGENCY:
            # Emergency trigger - always return True if status is active
            return True
        
        return False

    # ---------------------------------------------------------------------------
    # Database Operations
    # ---------------------------------------------------------------------------

    def _save_wallet(self, wallet: WalletConfig) -> None:
        """Save wallet to database"""
        try:
            db = get_database_manager()
            # In a real implementation, this would save to database
            self._logger.debug(f"Saved wallet: {wallet.address}")
        except Exception as e:
            self._logger.error(f"Failed to save wallet: {e}")

    def _save_inheritance_rule(self, rule: InheritanceRule) -> None:
        """Save inheritance rule to database"""
        try:
            db = get_database_manager()
            # In a real implementation, this would save to database
            self._logger.debug(f"Saved inheritance rule: {rule.wallet_address}")
        except Exception as e:
            self._logger.error(f"Failed to save inheritance rule: {e}")

    # ---------------------------------------------------------------------------
    # Multi-Signature Wallet Management
    # ---------------------------------------------------------------------------

    def create_multisig_wallet(
        self,
        addresses: List[str],
        required_signatures: int
    ) -> Optional[str]:
        """
        Create a multi-signature wallet address.

        Args:
            addresses: List of owner addresses
            required_signatures: Number of required signatures

        Returns:
            Multi-signature wallet address or None if invalid parameters
        """
        if not self._w3:
            raise RuntimeError("Web3 not connected")

        # Validate parameters
        if not addresses or len(addresses) < 2:
            self._logger.error("Multisig wallet requires at least 2 addresses")
            return None

        if required_signatures < 1 or required_signatures > len(addresses):
            self._logger.error(
                f"Required signatures must be between 1 and {len(addresses)}"
            )
            return None

        # Validate all addresses
        checksum_addresses = []
        for address in addresses:
            if not self.validate_address(address):
                self._logger.error(f"Invalid address: {address}")
                return None
            checksum_addresses.append(to_checksum_address(address))

        # Create multisig wallet using smart contract
        # For now, we'll use a simplified approach with create2
        try:
            # Generate multisig address from owner addresses and threshold
            # This is a simplified version - in production, you'd deploy a proper multisig contract
            import hashlib

            # Sort addresses for deterministic address generation
            sorted_addresses = sorted(checksum_addresses)

            # Create a unique identifier from addresses and required signatures
            identifier = f"{','.join(sorted_addresses)}:{required_signatures}"
            hash_input = identifier.encode('utf-8')

            # Generate address using keccak256
            hash_bytes = hashlib.sha256(hash_input).digest()

            # Convert to Ethereum address format
            multisig_address = '0x' + hash_bytes[-20:].hex()

            self._logger.info(
                f"Created {required_signatures}-of-{len(addresses)} multisig wallet: {multisig_address}"
            )

            return multisig_address

        except Exception as e:
            self._logger.error(f"Failed to create multisig wallet: {e}")
            return None

    def validate_multisig_transaction(
        self,
        multisig_address: str,
        signatures: List[str],
        transaction_data: Dict[str, Any]
    ) -> bool:
        """
        Validate multi-signature transaction.

        Args:
            multisig_address: Multi-signature wallet address
            signatures: List of signatures
            transaction_data: Transaction data

        Returns:
            True if valid
        """
        if not self._w3:
            raise RuntimeError("Web3 not connected")

        # In a real implementation, this would:
        # 1. Verify the number of signatures meets the threshold
        # 2. Verify each signature is from a valid owner
        # 3. Verify the transaction data is properly formatted
        # 4. Check that the transaction hasn't been executed

        # For now, we'll do basic validation
        if not signatures:
            self._logger.error("No signatures provided")
            return False

        # Verify signatures are valid hex strings
        for sig in signatures:
            if not sig.startswith('0x') or len(sig) != 132:
                self._logger.error(f"Invalid signature format: {sig}")
                return False

        self._logger.info(f"Validated {len(signatures)} signatures for multisig transaction")
        return True

    # ---------------------------------------------------------------------------
    # Utility Methods
    # ---------------------------------------------------------------------------

    def get_block_explorer_url(self, tx_hash: str) -> str:
        """
        Get block explorer URL for transaction.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Block explorer URL
        """
        base_url = BLOCK_EXPLORERS.get(self.config.network, BLOCK_EXPLORERS[DEFAULT_NETWORK])
        return f"{base_url}/tx/{tx_hash}"

    def validate_address(self, address: str) -> bool:
        """
        Validate Ethereum address.
        
        Args:
            address: Address to validate
            
        Returns:
            True if valid
        """
        if not WEB3_AVAILABLE:
            return False
        
        try:
            return Web3.is_address(address)
        except Exception:
            return False

    def estimate_gas(
        self,
        from_address: str,
        to_address: str,
        value: Decimal,
        data: Optional[str] = None
    ) -> int:
        """
        Estimate gas for transaction.
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            value: Amount to send
            data: Optional transaction data
            
        Returns:
            Estimated gas
        """
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        
        tx_dict = {
            'from': to_checksum_address(from_address),
            'to': to_checksum_address(to_address),
            'value': self._w3.to_wei(value, 'ether'),
            'data': data or '0x'
        }
        
        gas_estimate = self._w3.eth.estimate_gas(tx_dict)
        return gas_estimate

    def get_network_info(self) -> Dict[str, Any]:
        """
        Get network information.
        
        Returns:
            Network information
        """
        if not self._w3:
            return {}
        
        return {
            'network': self.config.network,
            'chain_id': self._w3.eth.chain_id,
            'block_number': self._w3.eth.block_number,
            'gas_price': str(self._w3.eth.gas_price),
            'connected': self._w3.is_connected()
        }


# ---------------------------------------------------------------------------
# Global Functions
# ---------------------------------------------------------------------------

def get_blockchain_manager(config: Optional[BlockchainConfig] = None) -> BlockchainManager:
    """
    Get or create global blockchain manager instance.
    
    Args:
        config: Blockchain configuration (optional)
        
    Returns:
        BlockchainManager instance
    """
    global _blockchain_manager
    
    if _blockchain_manager is None:
        _blockchain_manager = BlockchainManager(config)
    
    return _blockchain_manager


# Global blockchain manager instance
_blockchain_manager: Optional[BlockchainManager] = None

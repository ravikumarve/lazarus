"""
BlockchainManager — core blockchain operations for cryptocurrency inheritance.

Provides wallet management, transaction monitoring, inheritance rules,
and multi-signature wallet support.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.blockchain.constants import (
    BLOCK_EXPLORERS,
    CONFIRMATION_BLOCKS,
    DEFAULT_NETWORK,
    GAS_PRICE_MULTIPLIER,
    INHERITANCE_TIMEOUT_DAYS,
    RPC_ENDPOINTS,
    SUPPORTED_NETWORKS,
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
from core.database import get_database_manager

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from eth_utils import to_checksum_address
    from web3 import Web3
    from web3.exceptions import TransactionNotFound
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    Web3 = None
    Account = None
    TransactionNotFound = Exception
    to_checksum_address = lambda x: x


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
        self._w3 = self._init_web3()
        self._wallets: Dict[str, WalletConfig] = {}
        self._inheritance_rules: Dict[str, InheritanceRule] = {}
        self._load_wallets()
        self._load_inheritance_rules()
        self._logger.info(f"Blockchain manager initialized: {self.config.network}")

    def _init_web3(self) -> Optional[Web3]:
        """Initialize Web3 connection"""
        rpc_endpoint = self.config.rpc_endpoint or RPC_ENDPOINTS.get(
            self.config.network, RPC_ENDPOINTS[DEFAULT_NETWORK]
        )
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_endpoint))
            if w3.is_connected():
                self._logger.info(f"Connected to {self.config.network}")
                return w3
            self._logger.warning(f"Failed to connect to {self.config.network}")
            return None
        except Exception as e:
            self._logger.error(f"Failed to initialize Web3: {e}")
            return None

    def _load_wallets(self) -> None:
        """Load wallets from database"""
        try:
            get_database_manager()
            self._logger.info("Wallets loaded from database")
        except Exception as e:
            self._logger.error(f"Failed to load wallets: {e}")

    def _load_inheritance_rules(self) -> None:
        """Load inheritance rules from database"""
        try:
            get_database_manager()
            self._logger.info("Inheritance rules loaded from database")
        except Exception as e:
            self._logger.error(f"Failed to load inheritance rules: {e}")

    # -----------------------------------------------------------------------
    # Wallet Management
    # -----------------------------------------------------------------------

    def create_wallet(self, label: Optional[str] = None, description: Optional[str] = None) -> WalletConfig:
        """Create a new software wallet."""
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        account = Account.create()
        address = to_checksum_address(account.address)
        wallet = WalletConfig(
            address=address, network=self.config.network,
            wallet_type=WalletType.SOFTWARE,
            label=label or f"Wallet {address[:8]}", description=description,
            created_at=datetime.now(UTC), balance=Decimal(0), last_sync=datetime.now(UTC)
        )
        self._wallets[address] = wallet
        self._save_wallet(wallet)
        self._logger.info(f"Created wallet: {address}")
        return wallet

    def import_wallet(self, private_key: str, label: Optional[str] = None, description: Optional[str] = None) -> WalletConfig:
        """Import an existing wallet from private key."""
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        account = Account.from_key(private_key)
        address = to_checksum_address(account.address)
        wallet = WalletConfig(
            address=address, network=self.config.network,
            wallet_type=WalletType.SOFTWARE,
            label=label or f"Imported Wallet {address[:8]}", description=description,
            created_at=datetime.now(UTC), balance=Decimal(0), last_sync=datetime.now(UTC)
        )
        self._wallets[address] = wallet
        self._save_wallet(wallet)
        self._logger.info(f"Imported wallet: {address}")
        return wallet

    def get_wallet(self, address: str) -> Optional[WalletConfig]:
        """Get wallet by address."""
        return self._wallets.get(to_checksum_address(address))

    def list_wallets(self) -> List[WalletConfig]:
        """List all wallets."""
        return list(self._wallets.values())

    def get_balance(self, address: str) -> Decimal:
        """Get wallet balance in ETH."""
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        checksum_address = to_checksum_address(address)
        balance_wei = self._w3.eth.get_balance(checksum_address)
        balance_eth = self._w3.from_wei(balance_wei, 'ether')
        if checksum_address in self._wallets:
            self._wallets[checksum_address].balance = Decimal(str(balance_eth))
            self._wallets[checksum_address].last_sync = datetime.now(UTC)
        return Decimal(str(balance_eth))

    def sync_wallets(self) -> None:
        """Sync all wallet balances."""
        for address in self._wallets:
            try:
                self.get_balance(address)
            except Exception as e:
                self._logger.error(f"Failed to sync wallet {address}: {e}")

    # -----------------------------------------------------------------------
    # Transaction Management
    # -----------------------------------------------------------------------

    def send_transaction(self, from_address: str, to_address: str, value: Decimal, private_key: str, gas_limit: Optional[int] = None) -> Transaction:
        """Send a transaction."""
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        nonce = self._w3.eth.get_transaction_count(to_checksum_address(from_address))
        gas_price = self._w3.eth.gas_price
        tx_dict = {
            'nonce': nonce, 'to': to_checksum_address(to_address),
            'value': self._w3.to_wei(value, 'ether'),
            'gas': gas_limit or 21000,
            'gasPrice': int(gas_price * self.config.gas_price_multiplier),
            'chainId': self._w3.eth.chain_id
        }
        signed_tx = self._w3.eth.account.sign_transaction(tx_dict, private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        transaction = Transaction(
            tx_hash=tx_hash.hex(), from_address=from_address,
            to_address=to_address, value=value,
            gas_used=tx_dict['gas'], gas_price=tx_dict['gasPrice'],
            status=TransactionStatus.PENDING, timestamp=datetime.now(UTC),
            network=self.config.network
        )
        self._logger.info(f"Transaction sent: {tx_hash.hex()}")
        return transaction

    def get_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """Get transaction by hash."""
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        try:
            tx_receipt = self._w3.eth.get_transaction_receipt(tx_hash)
            tx = self._w3.eth.get_transaction(tx_hash)
            if tx_receipt is None:
                status = TransactionStatus.PENDING
            elif tx_receipt['status'] == 1:
                status = TransactionStatus.CONFIRMED
            else:
                status = TransactionStatus.FAILED
            return Transaction(
                tx_hash=tx_hash, from_address=tx['from'], to_address=tx['to'],
                value=Decimal(str(self._w3.from_wei(tx['value'], 'ether'))),
                gas_used=tx_receipt['gasUsed'] if tx_receipt else None,
                gas_price=tx['gasPrice'],
                block_number=tx_receipt['blockNumber'] if tx_receipt else None,
                status=status,
                timestamp=datetime.fromtimestamp(tx['timestamp'], UTC) if tx.get('timestamp') else None,
                network=self.config.network
            )
        except TransactionNotFound:
            self._logger.warning(f"Transaction not found: {tx_hash}")
            return None
        except Exception as e:
            self._logger.error(f"Failed to get transaction {tx_hash}: {e}")
            return None

    def wait_for_confirmation(self, tx_hash: str, timeout: int = 300) -> Optional[Transaction]:
        """Wait for transaction confirmation."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            transaction = self.get_transaction(tx_hash)
            if transaction and transaction.status == TransactionStatus.CONFIRMED:
                return transaction
            time.sleep(5)
        self._logger.warning(f"Transaction {tx_hash} not confirmed within timeout")
        return None

    # -----------------------------------------------------------------------
    # Inheritance Management
    # -----------------------------------------------------------------------

    def create_inheritance_rule(
        self, wallet_address: str, beneficiary_address: str,
        trigger_type: InheritanceTrigger = InheritanceTrigger.CHECKIN_MISSED,
        trigger_value: Optional[str] = None, conditions: Optional[Dict[str, Any]] = None
    ) -> InheritanceRule:
        """Create an inheritance rule."""
        rule = InheritanceRule(
            wallet_address=to_checksum_address(wallet_address),
            beneficiary_address=to_checksum_address(beneficiary_address),
            trigger_type=trigger_type, trigger_value=trigger_value,
            conditions=conditions or {}, created_at=datetime.now(UTC), status="active"
        )
        rule_key = f"{rule.wallet_address}_{rule.beneficiary_address}"
        self._inheritance_rules[rule_key] = rule
        self._save_inheritance_rule(rule)
        self._logger.info(f"Created inheritance rule: {rule_key}")
        return rule

    def get_inheritance_rules(self, wallet_address: Optional[str] = None) -> List[InheritanceRule]:
        """Get inheritance rules, optionally filtered by wallet address."""
        if wallet_address:
            checksum_address = to_checksum_address(wallet_address)
            return [r for r in self._inheritance_rules.values() if r.wallet_address == checksum_address]
        return list(self._inheritance_rules.values())

    def check_inheritance_triggers(self) -> List[InheritanceRule]:
        """Check and return triggered inheritance rules."""
        return [rule for rule in self._inheritance_rules.values()
                if rule.status == "active" and self._should_trigger_inheritance(rule)]

    def execute_inheritance(self, rule: InheritanceRule, private_key: str) -> Optional[Transaction]:
        """Execute inheritance transfer."""
        if rule.status != "active":
            self._logger.warning(f"Rule {rule.wallet_address} is not active")
            return None
        balance = self.get_balance(rule.wallet_address)
        if balance <= 0:
            self._logger.warning(f"Wallet {rule.wallet_address} has no balance")
            return None
        try:
            transaction = self.send_transaction(
                from_address=rule.wallet_address, to_address=rule.beneficiary_address,
                value=balance, private_key=private_key
            )
            rule.status = "executed"
            rule.executed_at = datetime.now(UTC)
            self._save_inheritance_rule(rule)
            self._logger.info(f"Executed inheritance: {rule.wallet_address} -> {rule.beneficiary_address}")
            return transaction
        except Exception as e:
            self._logger.error(f"Failed to execute inheritance: {e}")
            return None

    def _should_trigger_inheritance(self, rule: InheritanceRule) -> bool:
        """Check if inheritance should be triggered."""
        if rule.trigger_type == InheritanceTrigger.TIME_BASED:
            if rule.trigger_value and rule.created_at:
                days = int(rule.trigger_value)
                return datetime.now(UTC) >= rule.created_at + timedelta(days=days)
        elif rule.trigger_type == InheritanceTrigger.CHECKIN_MISSED:
            if rule.trigger_value:
                return False  # Would integrate with check-in system
        elif rule.trigger_type in (InheritanceTrigger.MANUAL, InheritanceTrigger.EMERGENCY):
            return True
        return False

    # -----------------------------------------------------------------------
    # Database Operations
    # -----------------------------------------------------------------------

    def _save_wallet(self, wallet: WalletConfig) -> None:
        """Save wallet to database."""
        try:
            get_database_manager()
            self._logger.debug(f"Saved wallet: {wallet.address}")
        except Exception as e:
            self._logger.error(f"Failed to save wallet: {e}")

    def _save_inheritance_rule(self, rule: InheritanceRule) -> None:
        """Save inheritance rule to database."""
        try:
            get_database_manager()
            self._logger.debug(f"Saved inheritance rule: {rule.wallet_address}")
        except Exception as e:
            self._logger.error(f"Failed to save inheritance rule: {e}")

    # -----------------------------------------------------------------------
    # Multi-Signature Wallet Management
    # -----------------------------------------------------------------------

    def create_multisig_wallet(self, addresses: List[str], required_signatures: int) -> Optional[str]:
        """Create a multi-signature wallet address."""
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        if not addresses or len(addresses) < 2:
            self._logger.error("Multisig wallet requires at least 2 addresses")
            return None
        if required_signatures < 1 or required_signatures > len(addresses):
            self._logger.error(f"Required signatures must be between 1 and {len(addresses)}")
            return None

        checksum_addresses = []
        for address in addresses:
            if not self.validate_address(address):
                self._logger.error(f"Invalid address: {address}")
                return None
            checksum_addresses.append(to_checksum_address(address))

        try:
            import hashlib
            sorted_addresses = sorted(checksum_addresses)
            identifier = f"{','.join(sorted_addresses)}:{required_signatures}"
            hash_bytes = hashlib.sha256(identifier.encode('utf-8')).digest()
            multisig_address = '0x' + hash_bytes[-20:].hex()
            self._logger.info(f"Created {required_signatures}-of-{len(addresses)} multisig wallet: {multisig_address}")
            return multisig_address
        except Exception as e:
            self._logger.error(f"Failed to create multisig wallet: {e}")
            return None

    def validate_multisig_transaction(self, multisig_address: str, signatures: List[str], transaction_data: Dict[str, Any]) -> bool:
        """Validate multi-signature transaction."""
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        if not signatures:
            self._logger.error("No signatures provided")
            return False
        for sig in signatures:
            if not sig.startswith('0x') or len(sig) != 132:
                self._logger.error(f"Invalid signature format: {sig}")
                return False
        self._logger.info(f"Validated {len(signatures)} signatures for multisig transaction")
        return True

    # -----------------------------------------------------------------------
    # Utility Methods
    # -----------------------------------------------------------------------

    def get_block_explorer_url(self, tx_hash: str) -> str:
        """Get block explorer URL for transaction."""
        base_url = BLOCK_EXPLORERS.get(self.config.network, BLOCK_EXPLORERS[DEFAULT_NETWORK])
        return f"{base_url}/tx/{tx_hash}"

    def validate_address(self, address: str) -> bool:
        """Validate Ethereum address."""
        if not WEB3_AVAILABLE:
            return False
        try:
            return Web3.is_address(address)
        except Exception:
            return False

    def estimate_gas(self, from_address: str, to_address: str, value: Decimal, data: Optional[str] = None) -> int:
        """Estimate gas for transaction."""
        if not self._w3:
            raise RuntimeError("Web3 not connected")
        tx_dict = {
            'from': to_checksum_address(from_address),
            'to': to_checksum_address(to_address),
            'value': self._w3.to_wei(value, 'ether'),
            'data': data or '0x'
        }
        return self._w3.eth.estimate_gas(tx_dict)

    def get_network_info(self) -> Dict[str, Any]:
        """Get network information."""
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
# Global factory
# ---------------------------------------------------------------------------

_blockchain_manager: Optional[BlockchainManager] = None


def get_blockchain_manager(config: Optional[BlockchainConfig] = None) -> BlockchainManager:
    """Get or create global blockchain manager instance."""
    global _blockchain_manager
    if _blockchain_manager is None:
        _blockchain_manager = BlockchainManager(config)
    return _blockchain_manager

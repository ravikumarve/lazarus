"""
Blockchain data types: enums and dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional

from core.blockchain.constants import CONFIRMATION_BLOCKS, DEFAULT_NETWORK, GAS_PRICE_MULTIPLIER, INHERITANCE_TIMEOUT_DAYS


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
    trigger_value: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    status: str = "active"


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

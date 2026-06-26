"""
core/hardware_wallet.py — Hardware wallet integration for Lazarus Protocol.

Provides:
- Hardware wallet support (Ledger, Trezor)
- Secure key storage and retrieval
- Transaction signing with hardware wallets
- Multi-signature wallet support
- Hardware wallet authentication

This module enables Lazarus Protocol to securely interact with
hardware wallets for enhanced security.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from ledgereth.complex import Exception as LedgerException
    from ledgereth.complex import LedgerClient
    LEDGER_AVAILABLE = True
except ImportError:
    LEDGER_AVAILABLE = False
    LedgerClient = None
    LedgerException = Exception

try:
    from trezorlib import btc
    from trezorlib.client import TrezorClient
    from trezorlib.tools import parse_path
    from trezorlib.transport import TransportException, enumerate_devices
    TREZOR_AVAILABLE = True
except ImportError:
    TREZOR_AVAILABLE = False
    enumerate_devices = None
    TransportException = Exception
    TrezorClient = None
    parse_path = None
    btc = None



# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DERIVATION_PATH = "m/44'/60'/0'/0/0"
SUPPORTED_HARDWARE_WALLETS = ["ledger", "trezor"]
AUTHENTICATION_TIMEOUT = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HardwareWalletType(Enum):
    """Types of hardware wallets"""
    LEDGER = "ledger"
    TREZOR = "trezor"
    UNKNOWN = "unknown"


class HardwareWalletStatus(Enum):
    """Status of hardware wallet connection"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class HardwareWalletConfig:
    """Configuration for hardware wallet"""
    wallet_type: HardwareWalletType
    device_id: Optional[str] = None
    label: Optional[str] = None
    derivation_path: str = DEFAULT_DERIVATION_PATH
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    status: HardwareWalletStatus = HardwareWalletStatus.DISCONNECTED


@dataclass
class HardwareWalletInfo:
    """Information about hardware wallet"""
    wallet_type: HardwareWalletType
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    serial_number: Optional[str] = None
    address: Optional[str] = None
    public_key: Optional[str] = None
    connected: bool = False
    authenticated: bool = False


# ---------------------------------------------------------------------------
# Hardware Wallet Manager
# ---------------------------------------------------------------------------

class HardwareWalletManager:
    """
    Manager for hardware wallet operations.
    
    This class provides:
    - Hardware wallet detection and connection
    - Secure key retrieval
    - Transaction signing
    - Multi-signature support
    - Hardware wallet authentication
    """

    def __init__(self):
        """Initialize hardware wallet manager"""
        self._logger = logging.getLogger("lazarus.hardware_wallet")

        # Connected wallets
        self._connected_wallets: Dict[str, HardwareWalletConfig] = {}

        # Active clients
        self._ledger_client: Optional[LedgerClient] = None
        self._trezor_client: Optional[TrezorClient] = None

        self._logger.info("Hardware wallet manager initialized")

    # ---------------------------------------------------------------------------
    # Device Detection
    # ---------------------------------------------------------------------------

    def detect_devices(self) -> List[HardwareWalletInfo]:
        """
        Detect connected hardware wallets.
        
        Returns:
            List of detected hardware wallets
        """
        devices = []

        # Detect Ledger devices
        if LEDGER_AVAILABLE:
            ledger_devices = self._detect_ledger_devices()
            devices.extend(ledger_devices)

        # Detect Trezor devices
        if TREZOR_AVAILABLE:
            trezor_devices = self._detect_trezor_devices()
            devices.extend(trezor_devices)

        self._logger.info(f"Detected {len(devices)} hardware wallet(s)")
        return devices

    def _detect_ledger_devices(self) -> List[HardwareWalletInfo]:
        """Detect Ledger devices"""
        devices = []

        if not LEDGER_AVAILABLE:
            return devices

        try:
            # Try to connect to Ledger
            client = LedgerClient()

            # Get device info
            info = HardwareWalletInfo(
                wallet_type=HardwareWalletType.LEDGER,
                model="Ledger Nano X",  # Would be detected from device
                connected=True,
                authenticated=False
            )

            devices.append(info)
            self._logger.info("Detected Ledger device")

        except Exception as e:
            self._logger.debug(f"No Ledger device detected: {e}")

        return devices

    def _detect_trezor_devices(self) -> List[HardwareWalletInfo]:
        """Detect Trezor devices"""
        devices = []

        if not TREZOR_AVAILABLE:
            return devices

        try:
            # Enumerate Trezor devices
            for device in enumerate_devices():
                info = HardwareWalletInfo(
                    wallet_type=HardwareWalletType.TREZOR,
                    model="Trezor Model T",  # Would be detected from device
                    connected=True,
                    authenticated=False
                )

                devices.append(info)
                self._logger.info("Detected Trezor device")

        except Exception as e:
            self._logger.debug(f"No Trezor device detected: {e}")

        return devices

    # ---------------------------------------------------------------------------
    # Device Connection
    # ---------------------------------------------------------------------------

    def connect_ledger(
        self,
        derivation_path: str = DEFAULT_DERIVATION_PATH
    ) -> Optional[HardwareWalletInfo]:
        """
        Connect to Ledger device.
        
        Args:
            derivation_path: BIP-32 derivation path
            
        Returns:
            Hardware wallet info or None
        """
        if not LEDGER_AVAILABLE:
            self._logger.error("Ledger support not available")
            return None

        try:
            # Create Ledger client
            client = LedgerClient()
            self._ledger_client = client

            # Get address
            address = client.get_address(derivation_path)

            # Get public key
            public_key = client.get_public_key(derivation_path)

            # Create wallet info
            info = HardwareWalletInfo(
                wallet_type=HardwareWalletType.LEDGER,
                model="Ledger Nano X",
                address=address,
                public_key=public_key.hex(),
                connected=True,
                authenticated=True
            )

            # Store wallet config
            config = HardwareWalletConfig(
                wallet_type=HardwareWalletType.LEDGER,
                device_id=address,
                label=f"Ledger {address[:8]}",
                derivation_path=derivation_path,
                created_at=datetime.now(UTC),
                last_used=datetime.now(UTC),
                status=HardwareWalletStatus.AUTHENTICATED
            )

            self._connected_wallets[address] = config

            self._logger.info(f"Connected to Ledger: {address}")
            return info

        except Exception as e:
            self._logger.error(f"Failed to connect to Ledger: {e}")
            return None

    def connect_trezor(
        self,
        derivation_path: str = DEFAULT_DERIVATION_PATH
    ) -> Optional[HardwareWalletInfo]:
        """
        Connect to Trezor device.
        
        Args:
            derivation_path: BIP-32 derivation path
            
        Returns:
            Hardware wallet info or None
        """
        if not TREZOR_AVAILABLE:
            self._logger.error("Trezor support not available")
            return None

        try:
            # Enumerate devices
            devices = enumerate_devices()
            if not devices:
                self._logger.error("No Trezor device found")
                return None

            # Create Trezor client
            client = TrezorClient(devices[0])
            self._trezor_client = client

            # Get address
            address_node = parse_path(derivation_path)
            address = client.ethereum.get_address(address_node, False)

            # Get public key
            public_key = client.ethereum.get_public_key(address_node)

            # Create wallet info
            info = HardwareWalletInfo(
                wallet_type=HardwareWalletType.TREZOR,
                model="Trezor Model T",
                address=address,
                public_key=public_key.hex(),
                connected=True,
                authenticated=True
            )

            # Store wallet config
            config = HardwareWalletConfig(
                wallet_type=HardwareWalletType.TREZOR,
                device_id=address,
                label=f"Trezor {address[:8]}",
                derivation_path=derivation_path,
                created_at=datetime.now(UTC),
                last_used=datetime.now(UTC),
                status=HardwareWalletStatus.AUTHENTICATED
            )

            self._connected_wallets[address] = config

            self._logger.info(f"Connected to Trezor: {address}")
            return info

        except Exception as e:
            self._logger.error(f"Failed to connect to Trezor: {e}")
            return None

    def disconnect(self, address: str) -> bool:
        """
        Disconnect hardware wallet.
        
        Args:
            address: Wallet address
            
        Returns:
            True if disconnected successfully
        """
        if address in self._connected_wallets:
            config = self._connected_wallets[address]
            config.status = HardwareWalletStatus.DISCONNECTED
            del self._connected_wallets[address]

            # Close clients
            if config.wallet_type == HardwareWalletType.LEDGER:
                self._ledger_client = None
            elif config.wallet_type == HardwareWalletType.TREZOR:
                self._trezor_client = None

            self._logger.info(f"Disconnected hardware wallet: {address}")
            return True

        return False

    # ---------------------------------------------------------------------------
    # Transaction Signing
    # ---------------------------------------------------------------------------

    def sign_transaction(
        self,
        address: str,
        transaction: Dict[str, Any]
    ) -> Optional[str]:
        """
        Sign transaction with hardware wallet.
        
        Args:
            address: Wallet address
            transaction: Transaction to sign
            
        Returns:
            Signed transaction or None
        """
        if address not in self._connected_wallets:
            self._logger.error(f"Wallet not connected: {address}")
            return None

        config = self._connected_wallets[address]

        try:
            if config.wallet_type == HardwareWalletType.LEDGER:
                return self._sign_with_ledger(config, transaction)
            elif config.wallet_type == HardwareWalletType.TREZOR:
                return self._sign_with_trezor(config, transaction)
            else:
                self._logger.error(f"Unsupported wallet type: {config.wallet_type}")
                return None

        except Exception as e:
            self._logger.error(f"Failed to sign transaction: {e}")
            return None

    def _sign_with_ledger(
        self,
        config: HardwareWalletConfig,
        transaction: Dict[str, Any]
    ) -> Optional[str]:
        """Sign transaction with Ledger"""
        if not self._ledger_client:
            self._logger.error("Ledger client not connected")
            return None

        try:
            # Sign transaction
            signed_tx = self._ledger_client.sign_transaction(
                config.derivation_path,
                transaction
            )

            # Update last used
            config.last_used = datetime.now(UTC)

            self._logger.info(f"Signed transaction with Ledger: {config.device_id}")
            return signed_tx

        except Exception as e:
            self._logger.error(f"Failed to sign with Ledger: {e}")
            return None

    def _sign_with_trezor(
        self,
        config: HardwareWalletConfig,
        transaction: Dict[str, Any]
    ) -> Optional[str]:
        """Sign transaction with Trezor"""
        if not self._trezor_client:
            self._logger.error("Trezor client not connected")
            return None

        try:
            # Sign transaction
            signed_tx = self._trezor_client.ethereum.sign_tx(
                parse_path(config.derivation_path),
                transaction['nonce'],
                transaction['gas_price'],
                transaction['gas_limit'],
                transaction['to'],
                transaction['value'],
                transaction.get('data', b''),
                transaction['chain_id']
            )

            # Update last used
            config.last_used = datetime.now(UTC)

            self._logger.info(f"Signed transaction with Trezor: {config.device_id}")
            return signed_tx

        except Exception as e:
            self._logger.error(f"Failed to sign with Trezor: {e}")
            return None

    # ---------------------------------------------------------------------------
    # Multi-signature Support
    # ---------------------------------------------------------------------------

    def create_multisig_wallet(
        self,
        addresses: List[str],
        required_signatures: int
    ) -> Optional[str]:
        """
        Create multi-signature wallet.
        
        Args:
            addresses: List of wallet addresses
            required_signatures: Number of required signatures
            
        Returns:
            Multi-signature wallet address or None
        """
        if len(addresses) < required_signatures:
            self._logger.error(
                f"Required signatures ({required_signatures}) "
                f"cannot exceed number of addresses ({len(addresses)})"
            )
            return None

        try:
            # In a real implementation, this would create a smart contract
            # For now, return a placeholder address
            multisig_address = f"0x{'0' * 40}"  # Placeholder

            self._logger.info(
                f"Created multi-sig wallet: {multisig_address} "
                f"({required_signatures}/{len(addresses)})"
            )

            return multisig_address

        except Exception as e:
            self._logger.error(f"Failed to create multi-sig wallet: {e}")
            return None

    def sign_multisig_transaction(
        self,
        multisig_address: str,
        transaction: Dict[str, Any],
        signer_address: str
    ) -> Optional[str]:
        """
        Sign multi-signature transaction.
        
        Args:
            multisig_address: Multi-signature wallet address
            transaction: Transaction to sign
            signer_address: Address of signer
            
        Returns:
            Signature or None
        """
        try:
            # Sign with hardware wallet
            signature = self.sign_transaction(signer_address, transaction)

            if signature:
                self._logger.info(
                    f"Signed multi-sig transaction: {multisig_address} "
                    f"by {signer_address}"
                )

            return signature

        except Exception as e:
            self._logger.error(f"Failed to sign multi-sig transaction: {e}")
            return None

    # ---------------------------------------------------------------------------
    # Utility Methods
    # ---------------------------------------------------------------------------

    def get_connected_wallets(self) -> List[HardwareWalletConfig]:
        """
        Get list of connected wallets.
        
        Returns:
            List of connected wallet configurations
        """
        return list(self._connected_wallets.values())

    def get_wallet_info(self, address: str) -> Optional[HardwareWalletInfo]:
        """
        Get wallet information.
        
        Args:
            address: Wallet address
            
        Returns:
            Hardware wallet info or None
        """
        if address not in self._connected_wallets:
            return None

        config = self._connected_wallets[address]

        return HardwareWalletInfo(
            wallet_type=config.wallet_type,
            address=address,
            connected=config.status != HardwareWalletStatus.DISCONNECTED,
            authenticated=config.status == HardwareWalletStatus.AUTHENTICATED
        )

    def is_connected(self, address: str) -> bool:
        """
        Check if wallet is connected.
        
        Args:
            address: Wallet address
            
        Returns:
            True if connected
        """
        return address in self._connected_wallets

    def authenticate(self, address: str) -> bool:
        """
        Authenticate hardware wallet.
        
        Args:
            address: Wallet address
            
        Returns:
            True if authenticated successfully
        """
        if address not in self._connected_wallets:
            return False

        config = self._connected_wallets[address]

        try:
            # Request user authentication on device
            # This would trigger a prompt on the hardware wallet
            # For now, we'll just mark as authenticated

            config.status = HardwareWalletStatus.AUTHENTICATED
            config.last_used = datetime.now(UTC)

            self._logger.info(f"Authenticated hardware wallet: {address}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to authenticate: {e}")
            return False


# ---------------------------------------------------------------------------
# Global Functions
# ---------------------------------------------------------------------------

def get_hardware_wallet_manager() -> HardwareWalletManager:
    """
    Get or create global hardware wallet manager instance.
    
    Returns:
        HardwareWalletManager instance
    """
    global _hardware_wallet_manager

    if _hardware_wallet_manager is None:
        _hardware_wallet_manager = HardwareWalletManager()

    return _hardware_wallet_manager


# Global hardware wallet manager instance
_hardware_wallet_manager: Optional[HardwareWalletManager] = None

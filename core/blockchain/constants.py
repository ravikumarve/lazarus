"""
Blockchain constants and configuration values.
"""

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

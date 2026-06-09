# License Validation Guide

This guide covers Gumroad license validation integration for Lazarus Protocol.

## Overview

The `core/license.py` module provides comprehensive license validation using Gumroad's API. It handles:

- License key validation
- Subscription status checking
- Wallet limit enforcement
- License expiration tracking
- Network error handling with retry logic
- Basic caching to reduce API calls

## Configuration

### Environment Variables

Set these environment variables in your `.env` file:

```bash
# Required: Gumroad product ID
GUMROAD_PRODUCT_ID=your_product_id_here

# Optional: Cache settings
LICENSE_CACHE_TTL=3600          # Cache TTL in seconds (default: 3600 = 1 hour)
LICENSE_MAX_RETRIES=3           # Maximum retry attempts (default: 3)
```

### Subscription Tiers

The system supports these subscription tiers with corresponding wallet limits:

| Tier | Wallet Limit | Description |
|------|-------------|-------------|
| Free | 1 wallet | Basic functionality |
| Basic | 3 wallets | Small-scale usage |
| Pro | 10 wallets | Professional usage |
| Enterprise | 50 wallets | Large-scale deployment |

## API Usage

### Basic License Validation

```python
from core.license import validate_license, LicenseValidationResult

# Validate a license key
try:
    result = validate_license("your_license_key_here")
    if result.valid:
        print(f"License valid! Tier: {result.subscription_tier}, "
              f"Wallet limit: {result.wallet_limit}")
    else:
        print(f"License invalid: {result.error_message}")
except Exception as e:
    print(f"Validation failed: {e}")
```

### Subscription Status Check

```python
from core.license import check_subscription_status

try:
    is_active = check_subscription_status("your_license_key_here")
    if is_active:
        print("Subscription is active")
    else:
        print("Subscription is not active")
except Exception as e:
    print(f"Status check failed: {e}")
```

### Wallet Limit Enforcement

```python
from core.license import verify_wallet_count

# Check if you can add another wallet
try:
    current_wallets = 2  # Your current wallet count
    verify_wallet_count("your_license_key_here", current_wallets)
    print("Can add more wallets")
except WalletLimitExceededError as e:
    print(f"Cannot add more wallets: {e}")
except Exception as e:
    print(f"Validation failed: {e}")
```

### License Expiration Check

```python
from core.license import is_license_expired

# Check if license has expired
if is_license_expired("your_license_key_here"):
    print("License has expired")
else:
    print("License is still valid")
```

## Error Handling

The module provides specific exception types for different error scenarios:

```python
from core.license import (
    LicenseError,
    InvalidLicenseError,
    NetworkError,
    SubscriptionExpiredError,
    WalletLimitExceededError
)

try:
    # Your license validation code here
    pass
except InvalidLicenseError as e:
    print(f"Invalid license: {e}")
except NetworkError as e:
    print(f"Network error: {e}")
except SubscriptionExpiredError as e:
    print(f"Subscription expired: {e}")
except WalletLimitExceededError as e:
    print(f"Wallet limit exceeded: {e}")
except LicenseError as e:
    print(f"License error: {e}")
```

## Caching

The module includes built-in caching to reduce API calls:

```python
from core.license import clear_license_cache, get_cache_stats

# Clear the cache (useful after license changes)
clear_license_cache()

# Get cache statistics
stats = get_cache_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"Cached keys: {stats['cache_entries']}")
```

## Integration with Configuration

The license module integrates with the main configuration system:

```python
from core.config import load_config, save_config
from core.license import validate_license

# Load existing config
config = load_config()

# Validate and update license information
if config.license_key:
    try:
        result = validate_license(config.license_key)
        if result.valid:
            config.subscription_tier = result.subscription_tier.value
            config.wallet_limit = result.wallet_limit
            config.license_valid_until = result.license_valid_until
            save_config(config)
            print("License validated and config updated")
        else:
            print(f"Invalid license: {result.error_message}")
    except Exception as e:
        print(f"License validation failed: {e}")
```

## Testing

Run the test suite to verify license functionality:

```bash
python test_license.py
```

## Gumroad API Integration

The module uses Gumroad's official license verification API:

- **Endpoint**: `https://api.gumroad.com/v2/licenses/verify`
- **Method**: POST
- **Parameters**: `product_id`, `license_key`
- **Response**: JSON with success status and purchase details

### Response Format

Successful response:
```json
{
  "success": true,
  "purchase": {
    "product_name": "Lazarus Protocol Pro",
    "email": "customer@example.com",
    "id": "purchase_123",
    "refunded": false,
    "chargebacked": false,
    "subscription_ended_at": "2024-12-31T23:59:59Z"
  }
}
```

Failed response:
```json
{
  "success": false,
  "message": "License key not found"
}
```

## Network Resilience

The module includes robust network error handling:

- **Exponential backoff**: Retries with increasing delays (1s, 2s, 4s, ... max 60s)
- **Max retries**: Configurable retry limit (default: 3)
- **Timeout**: Configurable timeout (default: 30 seconds)
- **Error classification**: Distinguishes between network errors and invalid licenses

## Security Considerations

- License keys are never logged
- API responses are validated before processing
- Network errors are properly handled and reported
- Cache entries are automatically expired
- No sensitive data is stored in cache

## Troubleshooting

### Common Issues

1. **"GUMROAD_PRODUCT_ID environment variable not set"**
   - Set the `GUMROAD_PRODUCT_ID` environment variable

2. **"License key not found"**
   - Verify the license key is correct
   - Check that the product ID matches your Gumroad product

3. **Network errors**
   - Check internet connectivity
   - Verify Gumroad API is accessible
   - Increase timeout if needed

4. **Cache issues**
   - Use `clear_license_cache()` to reset the cache
   - Adjust `LICENSE_CACHE_TTL` for different caching behavior

### Debug Mode

Enable debug logging for detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Support

For issues with license validation:

1. Check the Gumroad dashboard for license status
2. Verify your product ID matches exactly
3. Test API connectivity with curl:
   ```bash
   curl -X POST https://api.gumroad.com/v2/licenses/verify \
     -d "product_id=YOUR_PRODUCT_ID&license_key=YOUR_LICENSE_KEY"
   ```
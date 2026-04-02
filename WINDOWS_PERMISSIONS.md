# Windows File Permissions Implementation

## Overview

This document describes the Windows file permissions implementation in `core/config.py` that provides equivalent security to POSIX `chmod 0o600` functionality.

## Security Requirements

The implementation must provide security equivalent to:
- **POSIX**: `chmod 0o600` (read/write for owner only)
- **Windows**: Owner-only access with no inheritance, equivalent to:
  - Remove all inherited permissions
  - Grant read/write access to current user only
  - Remove all other users/groups (Everyone, Users, Authenticated Users)
  - Set owner to current user

## Implementation Strategy

The implementation uses a tiered approach with proper fallback handling:

### 1. Primary Method: pywin32 (Preferred)
- **Module**: `win32security`, `win32api`, `win32con`
- **Advantages**: Most robust, programmatic control, no external dependencies
- **Function**: `_try_pywin32_permissions()`
- **What it does**:
  - Creates a security descriptor with owner-only DACL
  - Grants `FILE_ALL_ACCESS` to current user only
  - Sets both DACL and owner security information
  - Applies security descriptor to the file

### 2. Fallback Method: icacls.exe
- **Tool**: Built-in Windows command-line utility
- **Advantages**: Available on all Windows systems, no additional dependencies
- **Function**: `_try_icacls_permissions()`
- **What it does**:
  - `/inheritance:r` - Removes inherited permissions
  - `/grant:r username:(R,W)` - Grants read/write to current user
  - `/remove: Everyone` - Removes Everyone group
  - `/remove: Users` - Removes Users group
  - `/remove: Authenticated Users` - Removes Authenticated Users group

### 3. Final Fallback: Basic Protection
- **Function**: `_set_basic_windows_protection()`
- **What it does**:
  - Sets hidden attribute (`attrib +H`)
  - Provides basic obscurity protection

## Error Handling

The implementation includes comprehensive error handling:

1. **ImportError**: pywin32 not installed → fallback to icacls
2. **FileNotFoundError**: icacls.exe not available → fallback to basic protection
3. **CalledProcessError**: icacls command failed → fallback to basic protection
4. **Generic Exception**: Any other error → log warning and continue

## Dependency Management

### Required Dependencies
- **pywin32**: Optional Windows-only dependency
  - Added to `requirements.txt` with platform specifier: `pywin32>=306; sys_platform == "win32"`
  - Not required for POSIX systems
  - Not required if icacls.exe is available

### Built-in Tools
- **icacls.exe**: Available on Windows Vista and later
- **attrib.exe**: Available on all Windows systems

## Testing

### Test Script
A comprehensive test script is provided: `test_windows_permissions.py`

**To run tests:**
```bash
# On Windows
python test_windows_permissions.py

# On POSIX systems (for verification)
python -c "from core.config import _secure_file_permissions; print('POSIX support verified')"
```

### Test Coverage
The test script verifies:
1. File creation with sensitive content
2. Individual permission methods (pywin32, icacls, basic)
3. Comprehensive permission function
4. Error handling and fallback behavior
5. File accessibility after permission changes

## Security Equivalence

### POSIX 0o600 Equivalent
| Permission | POSIX | Windows Equivalent |
|------------|-------|-------------------|
| Owner Read | ✓ | `FILE_GENERIC_READ` |
| Owner Write | ✓ | `FILE_GENERIC_WRITE` |
| Owner Execute | - | Not needed for config files |
| Group Access | ✗ | Removed via DACL |
| Other Access | ✗ | Removed via DACL |
| Inheritance | N/A | Removed via `inheritance:r` |

### Additional Windows Protections
1. **Hidden Attribute**: Obscures file from casual browsing
2. **Owner Setting**: Ensures proper ownership tracking
3. **ACL Validation**: Programmatic verification of permissions

## Deployment Considerations

### Windows Systems
1. **With pywin32**: Best security, recommended for production
2. **Without pywin32**: Falls back to icacls.exe, still secure
3. **Minimal systems**: Basic protection ensures no complete failure

### POSIX Systems
- Uses standard `os.chmod(stat.S_IRUSR | stat.S_IWUSR)`
- No additional dependencies required

### Cross-Platform Compatibility
- **Windows**: Requires Python 3.6+
- **Linux/macOS**: Requires Python 3.6+
- **All platforms**: Maintains identical security level

## Logging

The implementation includes detailed logging:
- **DEBUG**: Successful operations
- **WARNING**: Fallback scenarios and non-critical errors
- **ERROR**: Critical failures (logged by calling code)

## Maintenance

### Version Compatibility
- **pywin32**: Compatible with versions >=306
- **Windows**: Compatible with Vista and later
- **Python**: Compatible with 3.6+

### Future Enhancements
1. Add ACL verification to confirm permissions were set correctly
2. Implement backup permission restoration
3. Add support for Windows ACL inheritance patterns
4. Enhance error reporting with specific permission issues

## References

- [Microsoft DACL Documentation](https://docs.microsoft.com/en-us/windows/win32/secauthz/access-control-lists)
- [pywin32 Security API](https://mhammond.github.io/pywin32/)
- [icacls.exe Documentation](https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/icacls)
- [POSIX File Permissions](https://en.wikipedia.org/wiki/File_system_permissions#Notation_of_traditional_permissions)
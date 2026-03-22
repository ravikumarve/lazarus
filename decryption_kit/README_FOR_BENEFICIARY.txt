================================================================================
                 LAZARUS PROTOCOL — DECRYPTION INSTRUCTIONS
================================================================================

FROM: Your Loved One

You are receiving this because someone you care about has not checked in for
their configured period. This is their Lazarus vault — a secure inheritance
package they prepared for you.

--------------------------------------------------------------------------------
WHAT IS IN THIS PACKAGE?
--------------------------------------------------------------------------------
1. encrypted_secrets.bin — The encrypted vault file
2. key_blob.txt — Your personal decryption key (encrypted to YOUR key only)
3. decrypt.py — The decryption program
4. README_FOR_BENEFICIARY.txt — This file

--------------------------------------------------------------------------------
WHAT YOU NEED
--------------------------------------------------------------------------------
1. Your RSA private key file (.pem) — They gave this to you during setup
2. Python 3.10 or newer installed on your computer
3. The cryptography library (run: pip install cryptography)

--------------------------------------------------------------------------------
STEP-BY-STEP INSTRUCTIONS
--------------------------------------------------------------------------------

Windows:
1. Extract this ZIP file to a folder
2. Open Command Prompt (Win+R, type "cmd", press Enter)
3. Navigate to the folder: cd Downloads\Lazarus
4. Install cryptography: pip install cryptography
5. Run: python decrypt.py --key key_blob.txt

macOS / Linux:
1. Extract this ZIP file to a folder
2. Open Terminal
3. Navigate to the folder: cd ~/Downloads/Lazarus
4. Install cryptography: pip3 install cryptography
5. Run: python3 decrypt.py --key key_blob.txt

WHAT HAPPENS NEXT:
- The program will ask for your private key file location
- If your key is password-protected, it will ask for your password
- Enter where you want to save the decrypted file
- The decryption will complete and your secrets will be available

--------------------------------------------------------------------------------
TROUBLESHOOTING
--------------------------------------------------------------------------------

"Module not found" error:
  → Run: pip install cryptography

"Authentication failed" error:
  → Wrong key file or corrupted archive
  → Contact the executor or try another key if you have backups

"Permission denied" error:
  → Run the terminal as administrator (Windows) or use sudo (Mac/Linux)

Cannot find key_blob.txt:
  → Make sure it's in the same folder as decrypt.py

Need help?
  → Contact the person who set this up, or their designated executor

--------------------------------------------------------------------------------
IMPORTANT SECURITY NOTES
--------------------------------------------------------------------------------

- This tool has NO internet connection and sends NOTHING anywhere
- Your privacy is fully protected — only YOU can decrypt this
- The decryption happens entirely on YOUR computer
- After decryption, store your secrets securely and delete temporary files

--------------------------------------------------------------------------------
ABOUT LAZARUS PROTOCOL
--------------------------------------------------------------------------------

Lazarus Protocol is a self-sovereign, automated dead man's switch.
It ensures your digital assets and important information are passed to your
loved ones if something happens to you.

This tool was created with privacy and security as top priorities.

================================================================================

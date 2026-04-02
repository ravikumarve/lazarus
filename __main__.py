"""
Allows running: python -m lazarus <command>
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from cli.main import cli

if __name__ == "__main__":
    cli()

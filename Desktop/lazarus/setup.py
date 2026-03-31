from setuptools import setup, find_packages

setup(
    name="lazarus-protocol",
    version="0.1.0",
    description="Self-hosted dead man's switch for crypto holders",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "cryptography>=41.0.0",
        "pycryptodome>=3.19.0",
        "click>=8.1.7",
        "rich>=13.6.0",
        "questionary>=2.0.1",
        "APScheduler>=3.10.4",
        "requests>=2.31.0",
        "sendgrid>=6.11.0",
        "python-telegram-bot>=20.6",
        "python-dotenv>=1.0.0",
        "pydantic>=2.4.0",
    ],
    entry_points={
        "console_scripts": [
            "lazarus=lazarus.cli.main:cli",
        ],
    },
)

from setuptools import setup, find_packages
import os

# Read the long description from README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="lazarus-protocol",
    version="0.1.0",
    description="Self-hosted dead man's switch for crypto holders",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Ravi Kumar",
    author_email="ravi@example.com",
    url="https://github.com/yourusername/lazarus-protocol",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
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
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "ruff>=0.1.0",
            "black>=23.0.0",
        ],
        "windows": [
            "pywin32>=306; sys_platform == 'win32'",
        ],
    },
    entry_points={
        "console_scripts": [
            "lazarus=cli.main:cli",
        ],
    },
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Security :: Cryptography",
        "Topic :: System :: Archiving :: Backup",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "Environment :: Console",
        "Natural Language :: English",
    ],
    keywords=[
        "security",
        "cryptocurrency",
        "dead-man-switch",
        "encryption",
        "backup",
        "crypto-wallet",
        "self-hosted",
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/lazarus-protocol/issues",
        "Source": "https://github.com/yourusername/lazarus-protocol",
        "Documentation": "https://github.com/yourusername/lazarus-protocol#readme",
    },
)

from setuptools import setup, find_packages

setup(
    name="lazarus",
    version="1.0.0",
    description="Self-hosted dead man's switch for crypto holders",
    author="Ravi Kumar",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "cryptography>=45.0.6",
        "click==8.1.7",
        "rich==13.7.0",
        "questionary==2.0.1",
        "APScheduler==3.10.4",
        "requests==2.31.0",
        "python-dotenv==1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "lazarus=cli.main:cli",
        ],
    },
)

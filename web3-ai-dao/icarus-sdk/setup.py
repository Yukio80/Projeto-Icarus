from setuptools import setup, find_packages

setup(
    name="icarus-sdk",
    version="0.1.0",
    description="SDK for building governance bots for Projeto Icarus DAO",
    packages=find_packages(),
    install_requires=["web3>=6.0.0", "python-dotenv>=1.0.0"],
    python_requires=">=3.10",
)

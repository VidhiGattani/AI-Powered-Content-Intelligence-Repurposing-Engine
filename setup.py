"""
Setup configuration for Content Repurposing Platform
"""
from setuptools import setup, find_packages

setup(
    name="content-repurposing-platform",
    version="0.1.0",
    description="AI-Powered Content Repurposing Platform",
    author="Content Repurposing Team",
    python_requires=">=3.11",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "boto3>=1.34.0",
        "botocore>=1.34.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "hypothesis>=6.90.0",
            "moto>=4.2.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "cdk": [
            "aws-cdk-lib>=2.100.0",
            "constructs>=10.0.0",
        ]
    },
)

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="tix-cli",
    version="0.8.0",
    author="Valentin Todorov",
    author_email="valentin.v.todorov@gmail.com",
    description="Lightning-fast terminal task manager with working auto-completion",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TheDevOpsBlueprint/tix-cli",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Utilities",
        "Topic :: System :: Shells",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
    ],
    python_requires=">=3.7",
    install_requires=[
        "click>=8.0.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "tix=tix.cli:cli",
        ],
    },
    keywords="task todo cli terminal productivity manager shell completion",
    project_urls={
        "Bug Reports": "https://github.com/TheDevOpsBlueprint/tix-cli/issues",
        "Source": "https://github.com/TheDevOpsBlueprint/tix-cli",
        "Documentation": "https://github.com/TheDevOpsBlueprint/tix-cli#readme",
    },
    include_package_data=True,
    zip_safe=False,
)
from setuptools import setup, find_packages

setup(
    name="drama-downloader",
    version="1.0.0",
    description="Multi-Platform Short Drama Extractor and Downloader Module",
    author="Antigravity",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
        "cryptography>=41.0.0",
    ],
    entry_points={
        "console_scripts": [
            "dramadl=drama_downloader.cli:main",
            "drama-downloader=drama_downloader.cli:main",
        ],
    },
    python_requires=">=3.8",
)

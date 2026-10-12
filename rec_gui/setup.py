"""Setup configuration for rec_gui package."""

from setuptools import setup, find_packages

package_name = "rec_gui"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    package_data={
        "rec_gui": ["resource/rec_gui.yaml"],
    },
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/rec_gui"],
        ),
        (
            f"share/{package_name}",
            ["resource/rec_gui.yaml"],
        ),
    ],
    install_requires=[
        "setuptools",
        "pyyaml",
        "customtkinter",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
        ],
    },
    author="ROS 2 Community",
    author_email="you@example.com",
    maintainer="Your Name",
    maintainer_email="you@example.com",
    url="https://github.com/jkk-research/rec_gui",
    description="A graphical user interface for MCAP recording with ROS 2",
    long_description=open("README.md").read() if open("README.md").read() else "",
    long_description_content_type="text/markdown",
    license="Apache License 2.0",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "rec_gui=rec_gui.rec_gui_node:main",
        ],
    },
)

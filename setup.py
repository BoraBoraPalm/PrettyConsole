from setuptools import setup, find_packages

setup(
    name="PrettyConsole_",                                # Name of the library
    version="0.1",
    packages=find_packages(),
    description="A pretty console for formatted output using colorama.",
    author="Your Name",
    url="https://github.com/BoraBoraPalm/PrettyConsole",  # Replace with your GitHub repo URL
    install_requires=[
        "colorama",                                       # Dependencies
    ],
)

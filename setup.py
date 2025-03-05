from setuptools import setup, find_packages

setup(
    name="prettyconsole",                                 # Name of the library
    version="0.1",
    packages=find_packages(),
    description="A library for pretty console outputs.",
    author="Markus Schuster",
    url="https://github.com/BoraBoraPalm/PrettyConsole",  # Replace with your GitHub repo URL
    install_requires=[
        "colorama",                                       # Dependencies
    ],
    python_requires=">=3.6",
)

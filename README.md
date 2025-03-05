# PrettyConsole

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)  
[![Python Version](https://img.shields.io/badge/Python-3.6%2B-blue.svg)](https://www.python.org/downloads/)

## What is PrettyConsole?

PrettyConsole is a lightweight Python library that enhances your terminal output by providing formatted, colorful messages and handy utilities for command-line applications. With PrettyConsole, you can:

- **Display Formatted Messages:** Easily print messages with statuses such as `success`, `error`, `warning`, and `info` using vibrant colors.
- **Automatic Text Wrapping:** Handle long messages by automatically inserting line breaks and indenting text.
- **Timer Utilities:** Start and stop timers to measure execution time for your code.
- **Collect and Print Lines:** Accumulate multiple lines of text and print them together as a grouped message.
- **User Interaction:** Prompt users with customizable confirmation messages.

## How to Install

You can install PrettyConsole directly from GitHub using pip:

```bash
pip install git+https://github.com/BoraBoraPalm/PrettyConsole.git
```

For development purposes, clone the repository and install it in editable mode:

```bash
git clone https://github.com/BoraBoraPalm/PrettyConsole.git
cd PrettyConsole_
pip install -e .
```

## Requirements

- **Python 3.6+**: PrettyConsole is built for modern versions of Python.
- **[colorama](https://pypi.org/project/colorama/)**: Used to render colored text on various platforms.

All dependencies will be automatically installed when you install PrettyConsole.

## Example Usages

Below is an example demonstrating various functionalities of PrettyConsole:

```python
from prettyconsole import Console
import time

# Print a success message
Console.printf('success', 'Operation completed successfully.')

# Start a timer
Console.start_timer()

# Reset the counter before printing additional messages
Console.reset_counter()

# Print an error message
Console.printf('error', 'An error occurred while processing data.')

# Simulate a delay to showcase timer functionality
time.sleep(1)

# Stop the timer and display the elapsed time
Console.stop_timer()

# Print a warning message
Console.printf('warning', 'Warning: Incomplete data detected.')

# Print a long output message that will be automatically indented
Console.printf('success',
               'This is a longer output message that needs indentation. '
               'It will span multiple lines and should be properly indented.')

# Print a long message with explicit line breaks
Console.printf('success',
               'This is a longer output message that needs indentation. '
               'It will span multiple lines and should be properly indented.\n'
               'This is a longer output message that needs indentation. '
               'It will span multiple lines and should be properly indented.\n'
               'This is a longer output message that needs indentation. '
               'It will span multiple lines and should be properly indented.')

# Collect multiple lines and print them together
Console.add_lines("A 1")
Console.add_lines("B")
Console.printf_collected_lines("info")
```

## Contributing

Contributions are welcome! If you have suggestions, bug reports, or feature requests, please open an issue or submit a pull request on GitHub.

## License

Distributed under the MIT License. See the [LICENSE](LICENSE) file for more details.
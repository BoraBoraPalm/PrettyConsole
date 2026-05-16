# PrettyConsole

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)  
[![Python Version](https://img.shields.io/badge/Python-3.6%2B-blue.svg)](https://www.python.org/downloads/)
![Version](https://img.shields.io/badge/Version-0.2-green.svg)

## What is PrettyConsole?

PrettyConsole is a lightweight Python library that enhances your terminal output by providing formatted, colorful messages and handy utilities for command-line applications. With PrettyConsole, you can:

- **Display Formatted Messages:** Easily print messages with statuses such as `success`, `error`, `warning`, and `info` using vibrant colors.
- **Automatic Text Wrapping:** Handle long messages by automatically inserting line breaks and indenting text.
- **Timer Utilities:** Start and stop timers to measure execution time for your code.
- **Collect and Print Lines:** Accumulate multiple lines of text and print them together as a grouped message.
- **User Interaction:** Prompt users with customizable confirmation messages.

What's New in Version 0.2:

- **Variable Line Width:** The max message length now auto-detects from your terminal width, with a manual override via `Console.set_max_message_length(N)` (handy for Jupyter notebooks, where the width cannot be queried automatically).
- **More Stable Text Wrapping:** Long URLs, file paths, and overlong manual lines get cleanly wrapped, while hyphenated names like `--option-flag` stay intact.
- **Caller Location for Debugging:** Add `debug=True` to any `printf` call to show `module.Class.method:line` below the message, or toggle it globally with `Console.set_debug_mode(True)`.
- **Tagged Collected Lines:** Group several lists of collected lines in parallel using the new `tag` parameter on `add_lines` and `printf_collected_lines`.
- **Raise on Error:** Pass an exception class to `raise_error` to print the message and then raise -- the log line stays visible right before the traceback.
- **Section Headers:** Use `Console.printf_section('Title')` to print a full-width bar that visually groups the output that follows.

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

Every user-facing feature of `Console`, one at a time. Each block shows the code and the output it produces.

In a real terminal `success` is green, `error` is red, `warning` is yellow and `info` is blue. Colors are stripped from the output blocks below for GitHub readability.

```python
from prettyconsole import Console
import time
```

### Basic status messages

```python
Console.printf('success', 'Operation completed successfully.')
Console.printf('error',   'An error occurred while processing data.')
Console.printf('warning', 'Warning: Incomplete data detected.')
Console.printf('info',    'Just an informational message.')
```

```text
[  1  ][ success ] >> Operation completed successfully.
[  2  ][  error  ] >> An error occurred while processing data.
[  3  ][ warning ] >> Warning: Incomplete data detected.
[  4  ][  info   ] >> Just an informational message.
```

### Long message -- automatic line breaks

When the message exceeds the resolved max width, it is wrapped automatically and each line is indented under the status header.

```python
Console.printf('info',
               'This is a longer output message that needs indentation. '
               'It will span multiple lines and should be properly indented.')
```

```text
[  5  ][  info   ] ---v  (automatic line breaks)
                      This is a longer output message that needs indentation. It will span multiple
                      lines and should be properly indented.
```

### Long message -- explicit line breaks

If the message already contains `\n`, those breaks are preserved exactly. Overlong individual lines still get wrapped, but breaks the user inserted stay where they are.

```python
Console.printf('success',
               'First line of the report.\n'
               'Second line under the same status header.\n'
               'Third and final line.')
```

```text
[  6  ][ success ] ---v
                      First line of the report.
                      Second line under the same status header.
                      Third and final line.
```

### Force long format with a custom annotation

`long_format=True` forces the `---v` arrow even on short messages, and `long_annotation` adds a label after the arrow.

```python
Console.printf('warning', 'Disk usage above threshold.',
               long_format=True, long_annotation='resource warning')
```

```text
[  7  ][ warning ] ---v  (resource warning)
                      Disk usage above threshold.
```

### Mute

`mute=True` suppresses the call entirely. Nothing is printed and the counter does not advance -- the next visible call picks up where the previous one left off.

```python
Console.printf('info', 'This call is muted.', mute=True)
```

```text
(no output)
```

### Per-call debug -- caller location

`debug=True` appends the caller location (`module.Class.method:line`) on a separate indented line.

```python
Console.printf('info', 'Per-call debug shows caller location.', debug=True)
```

```text
[  8  ][  info   ] >> Per-call debug shows caller location.
                      ↳ from __main__.<module>:29
```

### Global debug toggle

`set_debug_mode(True)` enables the caller location for every following `printf` call without touching the call sites.

```python
Console.set_debug_mode(True)
Console.printf('success', 'Global debug mode is on.')
Console.set_debug_mode(False)
```

```text
[  9  ][ success ] >> Global debug mode is on.
                      ↳ from __main__.<module>:33
```

### Variable max message length

The wrap width auto-detects from the terminal via `shutil.get_terminal_size`. Pin a fixed value with `set_max_message_length(N)`, restore auto-detection with `set_max_message_length(None)`.

```python
Console.set_max_message_length(60)
Console.printf('info', 'Pinned width to 60 columns -- narrower wrap than the default.')
Console.set_max_message_length(None)
```

```text
[ 10  ][  info   ] ---v  (automatic line breaks)
                      Pinned width to 60 columns -- narrower
                      wrap than the default.
```

### Section header

A full-width white-background bar to visually group the output that follows. Does not advance the counter.

```python
Console.printf_section('Collected lines')
```

```text
SECTION: Collected lines
```

### Collected lines -- default tag

`add_lines` accumulates lines into a buffer, `printf_collected_lines` flushes the buffer in one `printf` call and clears it.

```python
Console.add_lines('Loaded file A.nii')
Console.add_lines('Loaded file B.nii')
Console.printf_collected_lines('info')
```

```text
[ 11  ][  info   ] ---v  (collected several lines)
                      Loaded file A.nii
                      Loaded file B.nii
```

### Collected lines -- multiple tags in parallel

Lines can be grouped under different tags and flushed independently. `show_tag=True` adds the tag name to the annotation.

```python
Console.add_lines('Step 1 done', tag='pipeline')
Console.add_lines('Step 2 done', tag='pipeline')
Console.add_lines('Score: 0.91', tag='metrics')
Console.printf_collected_lines('success', tag='pipeline', show_tag=True)
Console.printf_collected_lines('success', tag='metrics',  show_tag=True)
```

```text
[ 12  ][ success ] ---v  (collected several lines [tag: pipeline])
                      Step 1 done
                      Step 2 done
[ 13  ][ success ] ---v  (collected several lines [tag: metrics])
                      Score: 0.91
```

### Counter reset

```python
Console.reset_counter()
Console.printf('info', 'Counter restarts at 1.')
```

```text
      RESET counter TO 1
[  1  ][  info   ] >> Counter restarts at 1.
```

### Timer

```python
Console.start_timer()
time.sleep(0.5)
Console.stop_timer()
```

```text
         START TIMER
         TOOK 0.5 sec
```

### Raising errors with a custom exception class

Passing an exception class to `raise_error` prints the message first, then raises the exception. This keeps the log line visible right before the traceback or the catch.

```python
class DataError(Exception):
    pass

try:
    Console.printf('error', 'Pipeline failed.', raise_error=DataError)
except DataError as e:
    Console.printf('success', f'Caught DataError: {e}')
```

```text
[  2  ][  error  ] >> Pipeline failed.
[  3  ][ success ] >> Caught DataError: Pipeline failed.
```

## Notes

- **Jupyter.** The rendered cell width is not queryable from Python. Either set `os.environ["COLUMNS"] = "140"` once at the top of the notebook, or pin a fixed value with `Console.set_max_message_length(140)`.
- **Clean terminate.** `Console.printf('error', '...', raise_error=True)` prints the message wrapped in `(!!!)` markers together with the caller location, then calls `sys.exit(1)` without a Python traceback. Omitted from the demo because it would stop execution.
- **Interactive helpers.** `Console.ask_user(...)` and `Console.check_condition(...)` are omitted from the demo because they either block on `input()` or call `sys.exit()` in their default paths.

## Contributing

Contributions are welcome! If you have suggestions, bug reports, or feature requests, please open an issue or submit a pull request on GitHub.

## License

Distributed under the MIT License. See the [LICENSE](LICENSE) file for more details.
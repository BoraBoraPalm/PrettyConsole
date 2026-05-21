from colorama import Fore, Back, Style
import traceback
import textwrap
import shutil
import time
import sys

class Console:
    # The 'normal' parameters
    __counter = 1                          # Global __counter which will increase with each call of the printf function.
    __max_message_length_override = None   # Manual width override set via @set_max_message_length. None = auto-detect from terminal.
    __max_message_length_fallback = 100    # Used when terminal size cannot be detected (e.g. plain Jupyter without $COLUMNS set).
    __max_message_length_min = 40          # Floor for the auto-detected width so very narrow terminals don't break the layout.
    __indent = " " * 22                    # Intent for the long text
    __time_previous = 0
    __collected_lines = {}                 # Tag -> collected string. Allows grouping lines under different tags.
    __debug_mode = False                   # Global toggle for caller location info (module.Class.method:line)

    # For shortening the traceback length
    __short_paths_levels = 0                    # Number of parent folders to keep above filename in tracebacks. 0 = disabled (Python default).
    __short_paths_hooked = False                # Tracks whether the traceback hooks are installed, to prevent double-patching.
    __short_paths_orig_extract_tb = None        # Holds the original traceback.extract_tb (classic API entry point).
    __short_paths_orig_summary_extract = None   # Holds the original traceback.StackSummary.extract (modern API used by TracebackException in 3.10+).
    __short_paths_orig_excepthook = None        # Holds the original sys.excepthook (uncaught exceptions in main thread).

    @staticmethod
    def set_debug_mode(enabled: bool) -> None:
        """
        Globally enable or disable caller location info for all printf calls. Useful to switch on during development
        without touching every call site.

        :param enabled: True to enable, False to disable.
        :return: None
        """
        Console.__debug_mode = enabled

    @staticmethod
    def set_max_message_length(length) -> None:
        """
        Manually pin the max message length used by @printf. Pass None to re-enable auto-detection from the terminal
        size. Useful in Jupyter, where the rendered cell width cannot be queried from Python -- the kernel only sees
        HTML/CSS that gets rendered later in the browser. Two practical patterns:
          - Set $COLUMNS at the top of the notebook (then auto-detection picks it up).
          - Call this method once with a fixed width and forget about it.

        :param length: An integer width in characters, or None to fall back to auto-detection.
        :return: None
        """
        Console.__max_message_length_override = length

    @staticmethod
    def set_short_traceback_paths(levels: int = 2) -> None:
        """
        Globally shorten file paths in Python tracebacks to filename + @levels parent folders. Useful in deeply nested
        project trees where the full absolute path adds noise and pushes the actual filename off the screen. So a path
        like /home/user/proj/src/utils/helpers.py becomes src/utils/helpers.py with the default @levels=2.

        Covers the places Python prints an exception in a single-threaded program:
          - Uncaught exceptions in the main thread (sys.excepthook)
          - Caught exceptions via traceback.print_exc / format_exc / format_tb / ...
          - Modern TracebackException API in Python 3.10+ (StackSummary.extract)
          - Exceptions raised via @printf with raise_error=SomeExceptionClass

        Safe to call multiple times: hooks are only installed once, subsequent calls just update @levels. Call once at
        the top of the main entry point, before any code that might raise.

        :param levels: How many parent folders to keep above the filename. Default 2. Pass 0 to leave Python defaults
                       untouched (no-op if not previously enabled).
        :return: None
        """
        Console.__short_paths_levels = levels

        if Console.__short_paths_hooked:        # Already patched -- just update @levels and return, no double-wrapping.
            return
        if levels <= 0:                         # No reason to install hooks for a disabled depth. User can re-call with levels >= 1 later.
            return

        # Patch the traceback module entry points used by caught exceptions. @extract_tb covers the classic API
        # (print_exc, format_exc, format_tb, ...). @StackSummary.extract covers the modern API used by
        # TracebackException in Python 3.10+, which is what traceback.print_exception(exc) routes through and which
        # does NOT go via @extract_tb -- so both need patching for full coverage.
        Console.__short_paths_orig_extract_tb = traceback.extract_tb
        traceback.extract_tb = Console.__short_paths_patched_extract_tb

        Console.__short_paths_orig_summary_extract = traceback.StackSummary.extract
        traceback.StackSummary.extract = staticmethod(Console.__short_paths_patched_summary_extract)

        # Patch the global exception hook for uncaught exceptions in the main thread.
        Console.__short_paths_orig_excepthook = sys.excepthook
        sys.excepthook = Console.__short_paths_excepthook

        Console.__short_paths_hooked = True

    @staticmethod
    def _get_max_message_length() -> int:
        """
        Resolve the current max message length. Resolution order:
          1. Manual override set via @set_max_message_length.
          2. Live terminal width from shutil.get_terminal_size (also honors $COLUMNS, which is the practical way to
             size things in Jupyter).
          3. The configured fallback constant.
        Resolved on every @printf call, so resizing a real terminal between calls just works without reconfiguring.

        :return: Width in characters available for the message line.
        """
        if Console.__max_message_length_override is not None:
            return Console.__max_message_length_override

        cols = shutil.get_terminal_size(fallback=(Console.__max_message_length_fallback, 24)).columns
        # Guard against absurdly narrow terminals -- below this floor the indented output looks worse than just wrapping.
        safety_margin = 0

        return max(Console.__max_message_length_min, cols - safety_margin)

    @staticmethod
    def _wrap_message_lines(message: str, width: int) -> list:
        """
        Wrap `message` into a list of lines, each at most `width` characters wide. Unified for both inputs that already
        contain "\n" and inputs that do not -- this is more stable than calling textwrap.fill on the whole string,
        because the latter only handles the no-"\n" case well. Specifically:
          - Existing "\n" in the input are treated as hard breaks and preserved exactly. Each resulting logical line is
            then word-wrapped independently, so an overlong manual line (e.g. a long URL or file path inside a
            multi-line message) also gets wrapped instead of overflowing the terminal.
          - Tokens longer than `width` (long URLs, file paths, identifiers) get hard-split via break_long_words=True
            (textwrap default) instead of being left to overflow.
          - break_on_hyphens=False avoids surprise breaks inside hyphenated names (kebab-case, option flags,
            file-like-names). textwrap defaults to True which is good for prose but bad for technical output.
          - tabsize=4 keeps tab-expanded width predictable (textwrap default is 8, which inflates width unexpectedly).
          - Blank input lines are preserved as blank output lines, so paragraph spacing survives.

        :param message: The full message string. May contain "\n".
        :param width: Target maximum width per line in characters. Values < 1 are clamped to 1.
        :return: List of wrapped lines without trailing "\n" on any element.
        """
        width = max(1, width)

        wrapped_lines = []
        for raw_line in message.split("\n"):
            # textwrap.wrap returns [] for empty / whitespace-only input -- treat that as a blank line so paragraph
            # spacing in the input survives wrapping.
            chunks = textwrap.wrap(raw_line, width=width, break_on_hyphens=False, tabsize=4)
            wrapped_lines.extend(chunks if chunks else [""])

        return wrapped_lines

    @staticmethod
    def _get_caller_info(stack_offset: int) -> str:
        """
        Return 'module.Class.method:line' or 'module.function:line' for the caller. Uses dotted module name instead of
        the absolute filesystem path so committed Jupyter outputs stay clean.

        :param stack_offset: How many frames up to look for the real caller.
        :return: Formatted string with module, optional class, function and line number.
        """
        try:
            frame = sys._getframe(stack_offset)
        except ValueError:
            return "<unknown>"

        module = frame.f_globals.get('__name__', '<module>')
        func_name = frame.f_code.co_name
        line_no = frame.f_lineno

        # Detect class via self/cls in the frame's locals (works for instance & classmethods).
        class_name = None
        if 'self' in frame.f_locals:
            class_name = type(frame.f_locals['self']).__name__
        elif 'cls' in frame.f_locals:
            cls = frame.f_locals['cls']
            if isinstance(cls, type):
                class_name = cls.__name__

        qualified = f"{module}.{class_name}.{func_name}" if class_name else f"{module}.{func_name}"
        return f"{qualified}:{line_no}"

    @staticmethod
    def _shorten_path(path: str) -> str:
        """
        Reduce the given path to its filename plus @__short_paths_levels parent folders. Falls back gracefully -- if
        the path has fewer folders than @__short_paths_levels, whatever is available is returned without raising.
        Windows backslashes are normalised so the result looks the same cross-platform.

        :param path: Full or relative file path.
        :return: Shortened path string.
        """
        parts = path.replace("\\", "/").split("/")     # Normalise Windows separators so the split works cross-platform.
        return "/".join(parts[-(Console.__short_paths_levels + 1):])

    @staticmethod
    def __short_paths_patched_extract_tb(tb, limit=None):
        """
        Drop-in replacement for traceback.extract_tb. Covers the classic API path: print_exc, format_exc, format_tb,
        print_exception (pre-3.10), and anything else built on extract_tb. Installed by @set_short_traceback_paths.
        """
        frames = Console.__short_paths_orig_extract_tb(tb, limit)
        for frame in frames:
            frame.filename = Console._shorten_path(frame.filename)
        return frames

    @staticmethod
    def __short_paths_patched_summary_extract(*args, **kwargs):
        """
        Drop-in replacement for traceback.StackSummary.extract. Covers the modern API used by TracebackException in
        Python 3.10+, which does NOT route through @extract_tb. Installed by @set_short_traceback_paths.
        """
        frames = Console.__short_paths_orig_summary_extract(*args, **kwargs)
        for frame in frames:
            frame.filename = Console._shorten_path(frame.filename)
        return frames

    @staticmethod
    def __short_paths_excepthook(exc_type, exc_value, exc_tb) -> None:
        """
        Replacement for sys.excepthook. Prints uncaught exceptions in the main thread with shortened paths. Mirrors
        Python's default formatting otherwise so the output still looks familiar. Installed by @set_short_traceback_paths.
        """
        frames = traceback.extract_tb(exc_tb)          # Already shortened via the patched @extract_tb above.
        print("Traceback (most recent call last):", file=sys.stderr)
        print("".join(traceback.format_list(frames)), end="", file=sys.stderr)
        print(f"{exc_type.__name__}: {exc_value}", file=sys.stderr)

    @staticmethod
    def printf(status: str,
               message: str,
               long_format: bool = False,
               long_annotation: str = "",
               mute: bool = False,
               raise_error=False,
               debug: bool = False,
               _stack_offset: int = 1) -> None:
        """
        A formatted output. The user can insert the status and the corresponding message.

        :param status: possible options as strings: success, error, warning.
        :param message: a desired string message with length <= max_message_length or a message which contains several
                        lines, where each line is <= max_message_length and ends with an \n. The max_message_length is
                        resolved at call time -- see @_get_max_message_length and @set_max_message_length.
        :param long_format: default is False. If true a special case, where several lines are printed and "--v" is displayed.
        :param long_annotation: default is "", thus empty string. Just use it if long_format is set to True. Then, an
                                annotation in form of (my annotation) is created after the arrow pointing to the text.
                                Thus: [ i ][ message ] ---v  (my annotation)
        :param mute: If true then no console output. Maybe useful for already implemented printf. Thus, no need to comment.
        :param raise_error: If status == "error", raise after printing. Pass an exception class (recommended) to allow
                            targeted catching, or True as a shortcut for a clean termination with caller info and no
                            Python traceback. Default False = no raise.
        :param debug: If True (or globally enabled via @set_debug_mode), append the caller location on a new line below
                      the message. Format: module.Class.method:line
        :param _stack_offset: Internal. How many frames up to look for the caller. Used by wrappers like
                              @printf_collected_lines to skip themselves.
        :return: None
        """
        if mute: return

        # For raise_error=True on an error status -> wrap the reason in (!!!) markers and add termination location
        # below. Forces long_format so both lines render indented under the status header.
        is_generic_terminate = (raise_error is True) and (status == "error")
        if is_generic_terminate:
            caller_loc = Console._get_caller_info(_stack_offset + 1)
            message = f"(!!!) {message} (!!!)\nProgram terminated at {caller_loc}"
            long_format = True

        # Colors for the respective status
        colors = {
            'success': Fore.LIGHTGREEN_EX,
            'error': Fore.LIGHTRED_EX,
            'warning': Fore.LIGHTYELLOW_EX,
            'info': Fore.LIGHTBLUE_EX,
        }

        # Resolve caller info once if debugging is on (either per-call or globally).
        show_debug = debug or Console.__debug_mode
        caller = Console._get_caller_info(_stack_offset + 1) if show_debug else None

        long_annotation = f" ({long_annotation})" if long_annotation != "" else ""

        # Resolve the max message length once per call. Same value is then used for both the "fits on one line" check
        # and the wrap_width below -- prevents inconsistent results if the terminal would get resized mid-call.
        max_len = Console._get_max_message_length()

        # Single-line fast path: only when the message comfortably fits AND has no manual "\n" AND long_format wasn't
        # requested. Everything else goes through the unified long-format path below.
        is_single_line = (len(message) <= max_len) and ("\n" not in message) and (long_format is False)

        if is_single_line:
            output = f"[{Console.__counter:^5}][{colors[status] + status + Style.RESET_ALL:^18}] >> {message}\n"
        else:
            # Unified long-format path: handles messages with and without "\n" identically. The wrap helper splits on
            # "\n" first (preserving the user's intended hard breaks) and word-wraps each logical line independently,
            # so overlong manual lines (long URLs, file paths) also get wrapped instead of overflowing the terminal.
            wrap_width = max_len - len(Console.__indent)
            lines = Console._wrap_message_lines(message, wrap_width)

            # Add "(automatic line breaks)" to the annotation only if wrapping actually inserted breaks beyond what the
            # user already provided. len(output_lines) > len(input_lines) means at least one logical line got split.
            input_logical_lines = message.split("\n")
            auto_suffix = " (automatic line breaks)" if len(lines) > len(input_logical_lines) else ""

            output = (f"[{Console.__counter:^5}][{colors[status] + status + Style.RESET_ALL:^18}] ---v "
                      f"{long_annotation}{auto_suffix}\n")
            for line in lines:
                output += Console.__indent + line + "\n"

        # Debug location on its own indented line so the message column stays clean for long and short messages alike.
        if show_debug:
            output += f"{Console.__indent}↳ from {caller}\n"

        print(output, end="")

        Console.__counter += 1  # Just increasing the global counter.

        # Raise after printing so the log line is visible right before the traceback.
        if raise_error and status == "error":
            if isinstance(raise_error, type) and issubclass(raise_error, BaseException):
                # Custom exception class -> raise as-is, user controls own message and catch behavior.
                raise raise_error(message)
            else:
                # raise_error=True -> message was already formatted above with (!!!) markers and caller info.
                # Just exit cleanly here, no Python traceback needed.
                sys.exit(1)

    @staticmethod
    def add_lines(line: str, tag: str = "default") -> None:
        """
        Add lines which can then be printed collected with @printf_collected_lines. Lines are grouped by tag, so several
        independent groups can be collected in parallel.

        :param line: Some string.
        :param tag: Optional tag to group lines under. Defaults to "default", so old call sites keep working unchanged.
        :return: Nothing
        """
        if tag not in Console.__collected_lines:
            Console.__collected_lines[tag] = ""
        Console.__collected_lines[tag] += line + "\n"

    @staticmethod
    def printf_collected_lines(status: str, tag: str = "default", show_tag: bool = False, mute: bool = False,
                               raise_error=False, debug: bool = False) -> None:
        """
        Print the collected lines by the method @add_lines for a specific tag, then clear the collected lines for that
        tag only.

        :param status: according to the statuses defined in @printf
        :param tag: The tag whose collected lines should be printed. Defaults to "default".
        :param show_tag: If True the tag name is appended to the annotation. Defaults to False.
        :param mute: mutes the output.
        :param raise_error: Passed through to @printf. If truthy and status == "error", raise after printing.
        :param debug: Passed through to @printf. If True, show caller location below the message.
        :return: Nothing
        """
        if tag not in Console.__collected_lines or Console.__collected_lines[tag] == "":
            Console.printf("warning", f"No collected lines found for tag '{tag}'.", mute=mute)
            return

        annotation = "collected several lines"
        if show_tag:
            annotation += f" [tag: {tag}]"

        # _stack_offset=2 so the debug info points at the caller of printf_collected_lines, not at this method itself.
        Console.printf(status, Console.__collected_lines[tag], long_format=True, long_annotation=annotation, mute=mute,
                       raise_error=raise_error, debug=debug, _stack_offset=2)
        Console.__collected_lines[tag] = ""

    @staticmethod
    def printf_section(title: str) -> None:
        """
        For creating a new section in the console. The background is set to white.

        :param title: Desired title of the section.
        :return: Nothing
        """
        print()
        title = f"SECTION: {title:100}"
        print(f"{Back.WHITE + title + Style.RESET_ALL}")

    @staticmethod
    def ask_user(message: str, exit_if_false: bool = True) -> bool:
        """
        To ask the user to continue or terminate the program. Another option is to return either True or False.
        Example usage: if the required estimated space exceeds the desired limit.

        :return: boolean
        """
        answer = input(f"{Back.LIGHTYELLOW_EX + Fore.BLACK + '[CONTINUE (y/n) ?]' + Style.RESET_ALL + ' >> '}{message} -> ").lower()
        if answer == "n":

            if exit_if_false is True:
                Console.printf("error", "The user has terminated the program!")
                sys.exit()
            else:
                return False

        return True

    @staticmethod
    def check_condition(logic_operation: bool, ask_continue: bool = False) -> None:
        """
        For simply check boolean operations and if they are not true then ask the user whether to continue the program. An example could be
        memory_used < 5 GB.

        :param logic_operation: only boolean operations allowed -> Thus, True or False as result.
        :param ask_continue: If True, the user will be asked to continue the program if the boolean operation is False or to exit. By default,
                            False, thus if boolean operation results in False, the program will be terminated automatically.
        :return: Nothing
        """
        if logic_operation:
            Console.printf("success", f"Logic operation {logic_operation}. Continue program.")
        else:
            if not ask_continue:
                Console.printf("error", f"Logic operation {logic_operation}. Terminate program.")
                sys.exit()
            else:
                answer = input(f"{Back.LIGHTCYAN_EX + Fore.BLACK + '[CONTINUE (y/n) ?] >> ' + Style.RESET_ALL} Logic operation {logic_operation}").lower()
                if answer:
                    Console.printf("info", "The user has terminated the program!")
                else:
                    Console.printf("error", f"Logic operation {logic_operation}. Terminate program.")
                    sys.exit()

    @staticmethod
    def reset_counter() -> None:
        """
        Reset the global __counter to 1. A message will be printed to the console.

        :return: None
        """
        print(f"{Back.WHITE}{'RESET counter TO 1':^30}{Style.RESET_ALL}")
        # global __counter
        Console.__counter = 1

    @staticmethod
    def start_timer() -> None:
        """
        Start the timer and stop it with @stop_timer

        :return: Nothing
        """
        print(f"{Back.LIGHTBLUE_EX + Fore.BLACK}{'START TIMER':^30}{Style.RESET_ALL}")
        Console.__time_previous = time.time()

    @staticmethod
    def stop_timer() -> None:
        """
        Stops the timer started with @start_timer and prints the time passed to the console.

        :return: Nothing
        """
        took_time = f"TOOK {round(time.time() - Console.__time_previous, 3)} sec"
        print(f"{Back.LIGHTBLUE_EX + Fore.BLACK}{took_time:^30}{Style.RESET_ALL}")


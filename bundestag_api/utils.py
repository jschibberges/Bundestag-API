# -*- coding: utf-8 -*-

from datetime import date, datetime


def is_iso8601(string):
    iso_format = "%Y-%m-%dT%H:%M:%S"
    try:
        datetime.strptime(string, iso_format)
        return True
    except ValueError:
        return False

def to_iso8601(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(value, str):
        return value
    raise ValueError("Expected datetime or ISO8601 string")

def to_date_string(value, param_name="date"):
    """Normalize a date filter to the "YYYY-MM-DD" format expected by the API.

    Accepts None, datetime.date, datetime.datetime or a "YYYY-MM-DD" string.
    """
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"{param_name} must use the format YYYY-MM-DD, got '{value}'.") from None
        return value
    raise ValueError(f"{param_name} must be a 'YYYY-MM-DD' string or a date/datetime object.")

def parse_args_to_dict(args):
    """Parse CLI arguments of the form key=value.

    Repeating a key (e.g. title=Klima title=Energie) collects the values in a list.
    """
    args_dict = {}
    for arg in args:
        # Split the argument on '=' which separates the parameter from its value
        if '=' in arg:
            key, val = arg.split('=', 1)
            # Optionally remove leading dashes from parameters
            key = key.lstrip('-')
            if key in args_dict:
                if not isinstance(args_dict[key], list):
                    args_dict[key] = [args_dict[key]]
                args_dict[key].append(val)
            else:
                args_dict[key] = val
    return args_dict

def parse_bool(value):
    """Parse a CLI boolean such as true/false, yes/no, 1/0."""
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in ("true", "1", "yes", "y", "ja"):
        return True
    if normalized in ("false", "0", "no", "n", "nein"):
        return False
    raise ValueError(f"Expected a boolean value (true/false), got '{value}'.")

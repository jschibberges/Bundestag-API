# -*- coding: utf-8 -*-

from datetime import datetime


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
        return value  # your existing is_iso8601 will validate
    raise ValueError("Expected datetime or ISO8601 string")

def parse_args_to_dict(args):
    args_dict = {}
    for arg in args:
        # Split the argument on '=' which separates the parameter from its value
        if '=' in arg:
            key, val = arg.split('=', 1)
            # Optionally remove leading dashes from parameters
            key = key.lstrip('-')
            args_dict[key] = val
    return args_dict

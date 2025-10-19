# -*- coding: utf-8 -*-
import sys
import json
from typing import cast

from .bta_wrapper import Resource, btaConnection
from .utils import parse_args_to_dict


def main():
    """Entry point for the command-line interface."""
    # very small demo CLI
    if len(sys.argv) < 3:
        print("Usage: python -m bundestag_api <resource> <search|get> key=val ... [output_file=path/to/file.json]")
        sys.exit(1)

    try:
        resource = cast(Resource, sys.argv[1])
        action = sys.argv[2]
        kwargs = parse_args_to_dict(sys.argv[3:])
    except IndexError:
        print("Usage: python -m bundestag_api <resource> <search|get> key=val ... [output_file=path/to/file.json]")
        sys.exit(1)

    # Pop the output file argument so it's not passed to the API
    output_file = kwargs.pop("output_file", None)

    # The API wrapper expects certain arguments as integers. This loop finds
    # them in the command-line arguments and converts them.
    numeric_args = [
        "limit", "fid",
        "drucksacheID", "plenaryprotocolID", "processID", "activityID",
        "personID", "procedure_positionID",
        "process_type_notation", "legislative_period"
    ]
    for key in numeric_args:
        if key in kwargs:
            try:
                kwargs[key] = int(kwargs[key])
            except (ValueError, TypeError):
                print(f"Error: Argument '{key}' must be an integer. Got '{kwargs[key]}'.")
                sys.exit(1)

    conn = btaConnection(apikey=kwargs.pop("apikey", None))

    data = None
    if action == "search":
        data = conn.query(resource=resource, **kwargs)
    elif action == "get":
        fid = kwargs.pop("fid", None)
        if fid is None:
            print("Error: 'get' action requires an 'fid' argument (e.g., fid=12345).")
            sys.exit(1)
        data = conn.query(resource=resource, fid=fid, **kwargs)
    else:
        print(f"Error: Unknown action '{action}'. Must be 'search' or 'get'.")
        sys.exit(1)

    # If an output file is specified, write to it. Otherwise, print to console.
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # The default return format is JSON, which is a list of dicts
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Output successfully saved to {output_file}")
        except (IOError, TypeError) as e:
            # TypeError could happen if user requests a non-JSON-serializable format like pandas
            print(f"Error writing to file {output_file}: {e}")
            if isinstance(e, TypeError):
                print("Hint: Ensure 'return_format' is not set or is 'json' when writing to a file.")
            sys.exit(1)
    else:
        # Pretty-print JSON to the console for readability
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
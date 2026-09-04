import argparse
import json
import sys

from .parser import parse


def _print_human(info, reveal: bool) -> None:
    data = info.to_dict(reveal=reveal)
    order = ["format", "scheme", "user", "password", "host", "port", "database"]
    width = max(len(k) for k in order) + 1
    for key in order:
        value = data[key]
        print(f"{key + ':':<{width}} {value if value is not None else '-'}")
    if data["params"]:
        print("params:")
        for k, v in data["params"].items():
            print(f"  {k}: {v}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="connstr",
        description="Parse a database connection string and show its parts.",
    )
    parser.add_argument(
        "connection_string",
        nargs="?",
        help="the connection string to parse; reads from stdin if omitted",
    )
    parser.add_argument(
        "--json", action="store_true", help="output as a single JSON object"
    )
    parser.add_argument(
        "--reveal",
        action="store_true",
        help="show the password in plain text instead of redacting it",
    )
    args = parser.parse_args(argv)

    text = args.connection_string
    if text is None:
        text = sys.stdin.read()
    text = text.strip()
    if not text:
        parser.error("no connection string given (pass it as an argument or pipe it on stdin)")

    info = parse(text)

    if args.json:
        print(json.dumps(info.to_dict(reveal=args.reveal), indent=2))
    else:
        _print_human(info, reveal=args.reveal)

    return 0


if __name__ == "__main__":
    sys.exit(main())

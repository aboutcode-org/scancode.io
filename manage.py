#!/usr/bin/env python

if __name__ == "__main__":
    import sys
    print(sys.argv)

    for i, arg in enumerate(sys.argv[1:], start=1):
        if arg.endswith("manage.py"):
            sys.argv.pop(i)

    from scancodeio import command_line

    command_line()

#!/usr/bin/env python

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        if sys.argv[0] == sys.argv[1]:
            sys.argv.pop(0)
    from scancodeio import command_line

    command_line()

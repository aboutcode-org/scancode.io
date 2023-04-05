#!/usr/bin/env python

import warnings

# Turn off the warnings for the following modules.
# This filtering needs to be applied before the modules are imported.
warnings.filterwarnings("ignore", module="extractcode")
warnings.filterwarnings("ignore", module="typecode")


if __name__ == "__main__":
    from scancodeio import command_line

    command_line()

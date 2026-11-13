#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clubzweisam.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django ist nicht installiert. Bitte die Requirements installieren."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

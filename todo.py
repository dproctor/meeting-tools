#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Devon Proctor <devon.proctor@gmail.com>
#
# Distributed under terms of the MIT license.
"""
Utilities for handling TODOs in meeting note files.
"""

from __future__ import print_function
import os
import sys
import argparse
import re
import datetime


# Only use colors if connected to active terminal.
class bcolors:
    HEADER = '\033[95m' if sys.stdout.isatty() else ''
    OKBLUE = '\033[94m' if sys.stdout.isatty() else ''
    OKGREEN = '\033[92m' if sys.stdout.isatty() else ''
    WARNING = '\033[93m' if sys.stdout.isatty() else ''
    FAIL = '\033[91m' if sys.stdout.isatty() else ''
    ENDC = '\033[0m' if sys.stdout.isatty() else ''
    BOLD = '\033[1m' if sys.stdout.isatty() else ''
    UNDERLINE = '\033[4m' if sys.stdout.isatty() else ''


def main(arguments):

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-n',
                        '--notes_dir',
                        help="Directory containing notes",
                        type=str)
    parser.add_argument('-o',
                        '--owner',
                        help="Only show todos belonging to owner",
                        type=str)
    parser.add_argument('-vo',
                        '--inverse_owner',
                        help="Only show todos not belonging to owner",
                        type=str)

    args = parser.parse_args(arguments)

    for meeting_id in os.listdir(args.notes_dir):
        meeting_dir = os.path.join(args.notes_dir, meeting_id)
        printed_meeting_id = False
        for note in os.listdir(meeting_dir):
            if not re.search("^\d\d\d\d-\d\d-\d\d.txt$", note):
                continue
            note_filename = os.path.join(args.notes_dir, meeting_id, note)
            with open(note_filename, "r") as f:
                # Paragraphs are TODO with surrounding context.
                paragraphs = []
                lines = []
                active_todo = False
                for l in f.readlines():
                    if l == '\n' or (active_todo and _line_contains_todo(l)):
                        if _paragraph_contains_todo(lines):
                            paragraphs.append({"lines": lines})
                            active_todo = True
                        lines = []
                        if l != "\n":
                            lines.append(l)
                        active_todo = False
                    else:
                        lines.append(l)
                    if _line_contains_todo(l):
                        active_todo = True

                # Maybe add the last paragraph
                if len(lines) > 0 and _paragraph_contains_todo(lines):
                    paragraphs.append({"lines": lines})

                filtered = []
                # Filter TODOs
                for p in paragraphs:
                    m = _get_metadata_from_todo(p["lines"])
                    if args.owner is not None:
                        if args.owner not in m["owners"]:
                            continue
                    if args.inverse_owner is not None:
                        if args.inverse_owner in m["owners"]:
                            continue
                    filtered.append(p)

                if len(filtered) == 0:
                    continue

                if not printed_meeting_id:
                    print("\n" + bcolors.HEADER + bcolors.UNDERLINE +
                          meeting_id + bcolors.ENDC)
                    printed_meeting_id = True
                print(bcolors.HEADER + note + bcolors.ENDC)

                i = 1
                for p in filtered:
                    print(bcolors.WARNING + "{}.".format(i) + bcolors.ENDC)
                    print(_print_paragraph(p["lines"]))
                    i += 1


def _paragraph_contains_todo(lines):
    for l in lines:
        if _line_contains_todo(l):
            return True
    return False


def _get_metadata_from_todo(lines):
    owners = set()
    deadline = None
    for l in lines:
        ms = re.findall(" *TODO\(([^\)]*)\)", l)
        if len(ms) == 0:
            continue
        for m in ms[0].split(','):
            try:
                deadline = datetime.datetime.strptime(m.strip(), '%Y-%m-%d')
            except ValueError:
                owners.add(m)
    return {"owners": owners, "deadline": deadline}


def _line_contains_todo(l):
    return re.match(" *TODO\(.*\)", l)


def _print_paragraph(lines):
    return "\r".join([_format_line(l) for l in lines]).rstrip()


def _format_line(l):
    # return l
    return re.sub(r'(TODO\([^\)]*\))', bcolors.OKGREEN + r'\1' + bcolors.ENDC,
                  l)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

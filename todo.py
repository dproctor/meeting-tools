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

import argparse
import datetime
import os
import re
import sys


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
    parser.add_argument(
        '-m',
        '--meeting_id',
        help="Regular expression on meeting id to filter todos",
        type=str)

    args = parser.parse_args(arguments)

    for meeting_id in os.listdir(args.notes_dir):
        meeting_dir = os.path.join(args.notes_dir, meeting_id)
        printed_meeting_id = False
        for note in os.listdir(meeting_dir):
            if not re.search(r"^\d\d\d\d-\d\d-\d\d.txt$", note):
                continue
            note_filename = os.path.join(args.notes_dir, meeting_id, note)
            with open(note_filename, "r") as f:
                # Paragraphs are TODO with surrounding context.
                paragraphs = []
                lines = []
                active_todo = False
                for line in f.readlines():
                    if line == '\n' or (active_todo
                                        and _line_contains_todo(line)):
                        if _paragraph_contains_todo(lines):
                            paragraphs.append({
                                "lines": lines,
                                "meeting_id": meeting_id
                            })
                            active_todo = True
                        lines = []
                        if line != "\n":
                            lines.append(line)
                        active_todo = False
                    else:
                        lines.append(line)
                    if _line_contains_todo(line):
                        active_todo = True

                # Maybe add the last paragraph
                if lines and _paragraph_contains_todo(lines):
                    paragraphs.append({
                        "lines": lines,
                        "meeting_id": meeting_id
                    })

                filtered = []
                # Filter TODOs
                for paragraph in paragraphs:
                    metadata = _get_metadata_from_todo(paragraph["lines"])
                    if args.owner is not None:
                        if args.owner not in metadata["owners"]:
                            continue
                    if args.inverse_owner is not None:
                        if args.inverse_owner in metadata["owners"]:
                            continue
                    if args.meeting_id is not None:
                        if not re.search(args.meeting_id,
                                         paragraph["meeting_id"]):
                            continue

                    filtered.append(paragraph)

                if not filtered:
                    continue

                if not printed_meeting_id:
                    print("\n" + bcolors.HEADER + bcolors.UNDERLINE +
                          meeting_id + bcolors.ENDC)
                    printed_meeting_id = True
                print(bcolors.HEADER + note + bcolors.ENDC)

                i = 1
                for paragraph in filtered:
                    print(bcolors.WARNING + "{}.".format(i) + bcolors.ENDC)
                    print(_print_paragraph(paragraph["lines"]))
                    i += 1


def _paragraph_contains_todo(lines):
    for line in lines:
        if _line_contains_todo(line):
            return True
    return False


def _get_metadata_from_todo(lines):
    owners = set()
    deadline = None
    for line in lines:
        items = re.findall(r" *TODO\(([^\)]*)\)", line)
        if not items:
            continue
        for item in items[0].split(','):
            item = item.strip()
            try:
                deadline = datetime.datetime.strptime(item, '%Y-%m-%d')
            except ValueError:
                owners.add(item)
    return {"owners": owners, "deadline": deadline}


def _line_contains_todo(line):
    return re.match(r" *TODO\(.*\)", line)


def _print_paragraph(lines):
    return "\r".join([_format_line(l) for l in lines]).rstrip()


def _format_line(line):
    return re.sub(r'(TODO\([^\)]*\))', bcolors.OKGREEN + r'\1' + bcolors.ENDC,
                  line)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

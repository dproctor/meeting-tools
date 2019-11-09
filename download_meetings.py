#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Devon Proctor <devon.proctor@gmail.com>
#
# Distributed under terms of the MIT license.
"""
Script to download meeting calendar, and create note files for each meeting.
"""

from __future__ import print_function

import argparse
import os
import re
import sys
import textwrap
from datetime import date, datetime
from html.parser import HTMLParser

import requests
from dateutil import tz
from ics import Calendar

EMAIL_PATTERN = r"([^@ :\"\'<>]+@[^@ :\"\'<>]+\.[^@ :\"\'<>]+)"

NOTE_TEMPLATE = """{date}.txt

:Author: {author}
:Email: {email}
:Date: {time}
:Meeting-Time: {meeting_start} - {meeting_end}

:Meeting-Participants:
{participants}

:Meeting-Description:
{description}

:Agenda:

:Notes:

"""

DATETIME_PRINT_PATTERN = "%Y-%m-%d:%H:%M:%S"


class EventDescriptionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        for line in d.split("<br>"):
            for line2 in line.split("\n"):
                self.fed.append(line2)

    def get_data(self):
        return self.fed

    def get_data_joined(self):
        return ''.join(self.fed)

    def reset(self):
        super().reset()
        self.fed = []


def main(arguments):
    """Main method"""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-n',
                        '--notes_dir',
                        help="Directory containing notes",
                        type=str)
    parser.add_argument('-c',
                        '--ics_url',
                        help="ics URL for meeting calendar",
                        type=str)
    parser.add_argument('-a', '--author', help="Author of notes", type=str)
    parser.add_argument('-email', '--email', help="Author email", type=str)
    parser.add_argument("-s",
                        "--start-date",
                        dest="start_date",
                        default=date.today(),
                        type=lambda d: datetime.strptime(d, '%Y-%m-%d').date(),
                        help="Date in the format yyyy-mm-dd")
    parser.add_argument("-e",
                        "--end-date",
                        dest="end_date",
                        default=date.today(),
                        type=lambda d: datetime.strptime(d, '%Y-%m-%d').date(),
                        help="Date in the format yyyy-mm-dd")

    args = parser.parse_args(arguments)

    c = Calendar(requests.get(args.ics_url).text)

    notes = []
    parser = EventDescriptionParser()
    for e in c.events:
        if e.begin.datetime.astimezone(tz.tzlocal()).date(
        ) < args.start_date or e.begin.datetime.astimezone(
                tz.tzlocal()).date() > args.end_date:
            continue
        parser.feed(e.description)
        description = parser.get_data()
        p = _parse_event_description(description, e)
        n = {
            "meeting_id":
            p["meeting_id"],
            "date":
            e.begin.date(),
            "start":
            e.begin.datetime.astimezone(
                tz.tzlocal()).strftime(DATETIME_PRINT_PATTERN),
            "end":
            e.end.datetime.astimezone(
                tz.tzlocal()).strftime(DATETIME_PRINT_PATTERN),
            "description":
            parser.get_data_joined(),
            "emails":
            p["emails"]
        }
        notes.append(n)
        parser.reset()
    for n in notes:
        note_dir = os.path.join(args.notes_dir, n["meeting_id"])
        if not os.path.isdir(note_dir):
            os.mkdir(note_dir)
        note_filename = os.path.join(note_dir, "{}.txt".format(n["date"]))
        if os.path.exists(note_filename):
            print("Ignoring existing file: {}".format(note_filename))
            continue
        print("Creating file: {}".format(note_filename))
        with open(note_filename, "w") as f:
            f.write(
                NOTE_TEMPLATE.format(
                    date=n["date"],
                    author=args.author,
                    email=args.email,
                    time=datetime.now().strftime(DATETIME_PRINT_PATTERN),
                    meeting_start=n["start"],
                    meeting_end=n["end"],
                    participants=n["emails"],
                    description=textwrap.indent(n["description"], '  ')))


def _parse_event_description(description: str, e):
    lines = description

    # Meeting ID
    assert len(
        lines) > 0, "Meeting ({}, {}, '{}') is missing meeting id".format(
            e.name, e.begin, description)
    meeting_id = lines[0]

    # Extract emails
    emails = set()
    for l in lines:
        m = re.findall(EMAIL_PATTERN, l)
        if m is None: continue
        for a in m:
            emails.add(a)
    return {
        "meeting_id": meeting_id,
        "emails": "\n".join([_print_participant(e) for e in emails])
    }


def _print_participant(p):
    return "  {email}".format(email=p)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

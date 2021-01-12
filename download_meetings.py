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
from typing import Dict

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

MEETING_NAME_TO_ID: Dict[str, str] = {
    "Backlog Grooming": "change-research-eng-backlog-grooming",
    "Devon / Pat": "change-research-pat-reilly",
    "Devon : Alex Chen": "change-research-alex-chen",
    "Devon : Alex": "change-research-alex-auritt",
    "Devon : Anand": "change-research-anand-gupta",
    "Devon : Chris": "change-research-chris-coke",
    "Devon : Jane": "change-research-jane-loria",
    "Devon : Jesus": "change-research-jesus-garcia",
    "Devon : Joe": "change-research-joe-hale",
    "Devon : Judah": "change-research-judah-newman",
    "Devon : Lauren": "change-research-lauren-goldstein",
    "Devon : Mike": "change-research-mike-greenfield",
    "Devon : Nancy": "change-research-nancy-zdunkewicz",
    "Devon : Nicole": "change-research-nicole-bare",
    "Devon : Serena": "change-research-serena-roosevelt",
    "Devon : Stephen": "change-research-stephen-clermont",
    "Sprint Planning": "change-research-eng-sprint-planning",
}


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
        return "".join(self.fed)

    def reset(self):
        super().reset()
        self.fed = []


def main(arguments):
    """Main method"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-n", "--notes_dir", help="Directory containing notes", type=str
    )
    parser.add_argument(
        "-c", "--ics_url", help="ics URL for meeting calendar", type=str
    )
    parser.add_argument("-a", "--author", help="Author of notes", type=str)
    parser.add_argument("-email", "--email", help="Author email", type=str)
    parser.add_argument(
        "-s",
        "--start-date",
        dest="start_date",
        default=date.today(),
        type=lambda d: datetime.strptime(d, "%Y-%m-%d").date(),
        help="Date in the format yyyy-mm-dd",
    )
    parser.add_argument(
        "-e",
        "--end-date",
        dest="end_date",
        default=date.today(),
        type=lambda d: datetime.strptime(d, "%Y-%m-%d").date(),
        help="Date in the format yyyy-mm-dd",
    )
    parser.add_argument(
        "-id",
        dest="meeting_id",
        help="Meeting id for manual entry creation. If -id is provided, then no calendar lookup is done.",
    )

    args = parser.parse_args(arguments)

    if args.meeting_id:
        _maybe_create_file(
            args.notes_dir,
            args.meeting_id,
            args.start_date,
            "MEETING_START_TIME",
            "MEETING_END_TIME",
            None,
            "MEETING_DESCRIPTION",
            args.author,
            args.email,
        )
        return
    c = Calendar(requests.get(args.ics_url).text)

    notes = []
    parser = EventDescriptionParser()
    print(c.events)
    for e in c.events:
        if (
            e.begin.datetime.astimezone(tz.tzlocal()).date() < args.start_date
            or e.begin.datetime.astimezone(tz.tzlocal()).date() > args.end_date
        ):
            continue
        if e.name not in MEETING_NAME_TO_ID:
            print("Ignoring {}".format(e.name))
            continue
        parser.feed(e.description)
        description = parser.get_data()
        p = _parse_event_description(description, e)
        n = {
            # "meeting_id": p["meeting_id"],
            "meeting_id": MEETING_NAME_TO_ID[e.name],
            "date": e.begin.date(),
            "start": e.begin.datetime.astimezone(tz.tzlocal()).strftime(
                DATETIME_PRINT_PATTERN
            ),
            "end": e.end.datetime.astimezone(tz.tzlocal()).strftime(
                DATETIME_PRINT_PATTERN
            ),
            "description": parser.get_data_joined(),
            "emails": p["emails"],
        }
        notes.append(n)
        parser.reset()
    for n in notes:
        _maybe_create_file(
            args.notes_dir,
            n["meeting_id"],
            n["date"],
            n["start"],
            n["end"],
            n["emails"],
            n["description"],
            args.author,
            args.email,
        )


def _maybe_create_file(
    note_dir: str,
    meeting_id: str,
    date: str,
    meeting_start: str,
    meeting_end: str,
    emails: str,
    description: str,
    author: str,
    email: str,
) -> None:
    note_dir = os.path.join(note_dir, meeting_id)
    if not os.path.isdir(note_dir):
        os.mkdir(note_dir)
    note_filename = os.path.join(note_dir, "{}.txt".format(date))
    if os.path.exists(note_filename):
        print("Ignoring existing file: {}".format(note_filename))
        return
    print("Creating file: {}".format(note_filename))
    with open(note_filename, "w") as f:
        f.write(
            NOTE_TEMPLATE.format(
                date=date,
                author=author,
                email=email,
                time=datetime.now().strftime(DATETIME_PRINT_PATTERN),
                meeting_start=meeting_start,
                meeting_end=meeting_end,
                participants=emails,
                description=textwrap.indent(description, "  "),
            )
        )


def _parse_event_description(description: str, e):
    lines = description

    # Meeting ID
    if not lines:
        return {"meeting_id": "", "emails": ""}
    assert len(lines) > 0, "Meeting ({}, {}, '{}') is missing meeting id".format(
        e.name, e.begin, description
    )
    meeting_id = lines[0]

    # Extract emails
    emails = set()
    for l in lines:
        m = re.findall(EMAIL_PATTERN, l)
        if m is None:
            continue
        for a in m:
            emails.add(a)
    return {
        "meeting_id": meeting_id,
        "emails": "\n".join([_print_participant(e) for e in emails]),
    }


def _print_participant(p):
    return "  {email}".format(email=p)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

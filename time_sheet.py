#! /usr/bin/env python
#
# Copyright 2020 Devon Proctor <devon.proctor@gmail.com>
#
# Distributed under terms of the MIT license.
"""
Prints time sheet from dev journal.
"""

from __future__ import print_function

import argparse
import datetime
import locale
import math
import os
import sys
from typing import Dict, List, Optional

import dateutil.parser

HOURLY_BILLING_RATE = 150.00


class Interval:
    def __init__(self):
        self.start: datetime = None
        self.end: datetime = None
        self.lines: List[str] = []

    def hours(self) -> datetime.timedelta:
        return (self.end - self.start).total_seconds() / 3600

    def validate(self) -> None:
        if self.end < self.start:
            raise ValueError(
                "Negative duration for interval:\n{}".format(self))

    def __str__(self):
        summary = "\n".join(["  {}".format(line) for line in self.lines[1:-1]])
        return "{} [{} - {}]\n{}".format("{:5.2f} hours".format(self.hours()),
                                         str(self.start), str(self.end),
                                         summary)


def _parse_timestamp_line(line):
    if not line.startswith("# "):
        return False
    try:
        time = dateutil.parser.parse(" ".join(line.split(" ")[1:3]))
    except ValueError:
        return False
    if not time:
        return False
    tags = [tag.strip() for tag in line.split(" ")[3:]]
    return {"time": time, "tags": tags}


def _parse_intervals_from_journal(lines: List[str], start_tag: str,
                                  end_tag: str) -> List[Interval]:
    intervals: List[Interval] = []
    active_interval: Optional[Interval] = None
    for num, line in enumerate(lines):
        parsed = _parse_timestamp_line(line)
        if not active_interval:
            if parsed:
                if end_tag in parsed["tags"]:
                    raise ValueError(
                        "Ending interval without starting it (line {}): {}".
                        format(num + 1, line))
                if start_tag in parsed["tags"]:
                    active_interval = Interval()
                    active_interval.start = parsed["time"]
                    active_interval.lines.append(line)
            else:
                continue
        else:
            if parsed:
                active_interval.lines.append(line)
                if start_tag in parsed["tags"]:
                    raise ValueError(
                        "Starting interval when already open (line {}): {}".
                        format(num + 1, line))
                if end_tag in parsed["tags"]:
                    active_interval.end = parsed["time"]
                    active_interval.validate()
                    intervals.append(active_interval)
                    active_interval = None
            else:
                active_interval.lines.append(line)
    if active_interval:
        raise ValueError("EOF reached. Interval not terminated.")
    return intervals


# pylint: disable=missing-docstring
def main(arguments):

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--start', help="Start tag", type=str, required=True)
    parser.add_argument('--end', help="End tag", type=str, required=True)
    parser.add_argument('--notes', help="Notes file", type=str, required=True)

    args = parser.parse_args(arguments)
    locale.setlocale(locale.LC_ALL, '')
    intervals: List[Interval]
    with open(args.notes) as fid:
        intervals = _parse_intervals_from_journal(fid.readlines(), args.start,
                                                  args.end)

    total_duration = sum([i.hours() for i in intervals])

    print("Total: {:.2f} = {}\n================================\n".format(
        total_duration,
        locale.currency(total_duration * HOURLY_BILLING_RATE, grouping=True)))
    for i in intervals:
        print(i)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

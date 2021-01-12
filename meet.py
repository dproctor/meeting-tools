#! /usr/bin/env python3
"""
Meeting command line tool.
"""

from __future__ import print_function

import argparse
import cmd
import datetime
import os
import sys
from pathlib import Path

NOTES_DIR = "/home/devon/notes/meeting_notes/"


# pylint: disable=missing-docstring
class meet(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        self.prompt = "(meet) "

    def do_quit(self, s):
        return True

    def do_add(self, s):
        mid, date = s.split(" ")
        mdir = os.path.join(NOTES_DIR, mid)
        if mid not in os.listdir(NOTES_DIR):
            os.mkdir(mdir)

        mpath = os.path.join(mdir, date + ".md")
        if os.path.exists(mpath):
            print("Meeting file exists: {}".format(mpath))
        else:
            Path(mpath).touch()

    def complete_add(self, text, line, begidx, endidx):
        args = line.split(" ")[1:]
        if len(args) < 2:
            mline = line.partition(" ")[2]
            offs = len(mline) - len(text)
            completions = os.listdir(NOTES_DIR)
            return [s[offs:] for s in completions if s.startswith(args[-1])]
        elif len(args) == 2:
            offs = len(args[-1]) - len(text)
            date = datetime.date.today().isoformat()
            return [date[offs:]] if date.startswith(args[-1]) else None
        else:
            return None


if __name__ == "__main__":
    meet().cmdloop()

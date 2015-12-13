#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import os

from docopt import docopt
from duplicates import start_logger
from duplicates.gatherer import Gatherer
from duplicates.libraries.output import ConsoleOutput
from schema import And, Optional, Or, Schema, SchemaError

log = logging.getLogger(__name__)


class CommandLineInterface(object):
    """Usage: %(name)s [options] DIRECTORY [PATTERNS...]

    You can filter the analysed files passing multiple patterns through command
    line, the patterns can include "Unix shell-style wildcards"

    Options:
        --show-content          print all the files analysed
        --show-duplicates       print files that have duplicates, duplicates path are separated by tabs
        --progress              print progress update in console
        --no-store              do not save the gathered information on filesystem
        --log-level=<LEVEL>     process debug level [default: CRITICAL]

    Examples:
        %(name)s .                  # every file
        %(name)s . '*.png'          # only .png files
        %(name)s . '*.png' '*.jpg'  # .png and .jpg files
    """

    def __init__(self):
        super(CommandLineInterface, self).__init__()

    def _validate_args(self, opt):
        schema = Schema({
            'DIRECTORY': And(os.path.exists, error="Dir does not exists"),
            Optional('--show-content'): bool,
            Optional('--show-duplicates'): bool,
            Optional('--progress'): bool,
            Optional('--no-store'): bool,
            Optional('--log-level'): Or(unicode, str),
            Optional('PATTERNS'): [Or(unicode, str)]
        })
        try:
            opt = schema.validate(opt)
        except SchemaError as e:
            exit(e)
        return opt

    def _parse_args(self, name=None):
        if name is None:
            name = __file__
        opt = docopt(self.__doc__ % {'name': name}, argv=None, help=True,
                     version=None, options_first=False)
        return self._validate_args(opt)

    def run(self, name=None):
        try:
            opt = self._parse_args(name)
            start_logger(opt['--log-level'])
            gatherer = Gatherer(
                opt['DIRECTORY'],
                output=ConsoleOutput(opt['--show-content'] or opt['--show-duplicates'], opt['--progress']),
                unix_patterns=opt['PATTERNS']
            ).run(not opt['--no-store'])

            if opt['--show-content']:
                gatherer.print_content()

            if opt['--show-duplicates']:
                gatherer.print_duplicates()

        except KeyboardInterrupt:
            log.exception('Exiting on CTRL^C')

if __name__ == '__main__':
    CommandLineInterface().run()
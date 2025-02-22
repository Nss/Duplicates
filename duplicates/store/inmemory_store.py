# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import logging
import os

from duplicates.fs.file_attr import Attributes, FileAttr
from duplicates.libraries.utils import (absolute_path, epoch, serialize_date)
from duplicates.store.dummy_store import DummyStore
from future.utils import viewitems

from munch import Munch

KNOWN_PATHNAMES_HASHES = 'known_pathnames_hashes'
PATHNAME_HASH_TO_ATTRS = 'pathname_hash_to_attrs'
FILE_HASH_TO_PATHNAMES = 'file_hash_to_pathnames'
FILTERS = 'filters'

SIZE = 'size'
LMTIME = 'lmtime'
HASH = 'hash'
PATHNAME = 'pathname'
LAST_UPDATE = 'updated'

log = logging.getLogger(__name__)


def updated(func):
    def func_wrapper(self, *args, **kwargs):
        self._set_last_update()
        return func(self, *args, **kwargs)
    return func_wrapper


class InmemoryStore(DummyStore):

    """Store information about duplicates

    The data are kept in a gziped json file inside the analized directory,
    all the pathnames in the filestore are "local", by "local" we intend a
    relative pathname from the filestore location.

    The store contains three main structures:

        KNOWN_PATHNAMES_HASHES:
            A list containing all the hashes of the known pathnames

        PATHNAME_HASH_TO_ATTRS:
            a dictionary with pathname_hash as key and file attributes
            (SIZE, LMTIME, HASH, PATHNAME) as value

        FILE_HASH_TO_PATHNAMES:
            a dictionary that has the file hash as key and a list of pathnames,
            of the files that generate that hash, as value

    """

    def __init__(self, directory):
        default_data = {
            KNOWN_PATHNAMES_HASHES: set([]),
            PATHNAME_HASH_TO_ATTRS: {},
            FILE_HASH_TO_PATHNAMES: {},
            LAST_UPDATE: serialize_date(epoch),
            FILTERS: None
        }
        super(InmemoryStore, self).__init__(default_data)
        self._directory = absolute_path(directory)

    def _local_path(self, abs_pathname):
        return abs_pathname.replace(self._directory, '.')

    def _absolute_pathname(self, local_pathname):
        abs_pathname = os.path.normpath(os.path.join(self._directory, local_pathname))
        log.debug('Absolute pathname for %s: %s', local_pathname, abs_pathname)
        return abs_pathname

    @updated
    def _add_file(self, file_attr):
        file_attr = Munch(file_attr)
        pathname = file_attr.pathname
        pathname_hash = file_attr.pathname_hash
        if file_attr.hash not in self.hash_to_pathnames:
            self.hash_to_pathnames[file_attr.hash] = []
        self.hash_to_pathnames[file_attr.hash].append(pathname)
        self._pathname_hash_to_attr[pathname_hash] = {
            SIZE: file_attr.size,
            LMTIME: file_attr.lmtime,
            HASH: file_attr.hash,
            PATHNAME: pathname
        }
        log.debug('Adding %s to the store', pathname)
        self._known_pathnames_hashes.add(pathname_hash)

    @updated
    def _remove_pathname(self, pathname):
        log.debug('Removing %s from the store', os.path.join(self._directory, pathname))
        pathname_hash = FileAttr.pathname_hash(self._directory, pathname)
        self._known_pathnames_hashes.remove(pathname_hash)
        stored_data = self._pathname_hash_to_attr[pathname_hash]
        self.hash_to_pathnames[stored_data[HASH]].remove(stored_data[PATHNAME])
        del(self._pathname_hash_to_attr[pathname_hash])
        log.debug('%s Removed', pathname)

    def add_file(self, file_attr):
        if not self.is_file_known(file_attr):
            self._add_file(file_attr)

    def is_file_known(self, file_attr):
        file_attr = Munch(file_attr)
        pathname_hash = file_attr.pathname_hash
        if pathname_hash not in self._known_pathnames_hashes:
            return False
        else:
            stored_attr = self._pathname_hash_to_attr[pathname_hash]
            diff_size = stored_attr[SIZE] != file_attr.size
            diff_time = stored_attr[LMTIME] != file_attr.lmtime
            if diff_size or diff_time:
                return False
            return True

    def filter_known_files(self, dircontent):
        attributes = set([Attributes.PATHNAME_HASH, Attributes.SIZE, Attributes.LMTIME])
        for directory, filepath in dircontent:
            attr = FileAttr.get(directory, filepath, attributes=attributes)
            if not self.is_file_known(attr):
                yield directory, filepath

    @property
    def filters(self):
        return self._data[FILTERS]

    @filters.setter
    @updated
    def filters(self, filters):
        self._data[FILTERS] = filters

    def clean(self):
        self._data[FILE_HASH_TO_PATHNAMES] = {k: v for k, v in viewitems(self.hash_to_pathnames) if v}

    def remove_pathname(self, pathname):
        self._remove_pathname(pathname)

    def relpaths_by_hash(self):
        for hash, paths in viewitems(self.hash_to_pathnames):
            yield hash, paths

    def hash_to_abs_pathnames(self, hash):
        if hash in self.hash_to_pathnames:
            return map(self._absolute_pathname, self.hash_to_pathnames[hash])

    def _set_last_update(self):
        self._data[LAST_UPDATE] = serialize_date(datetime.datetime.utcnow())

    def __repr__(self):
        return repr(self._data)

    def __len__(self):
        return len(self._known_pathnames_hashes)

    @property
    def _known_pathnames_hashes(self):
        return self._data[KNOWN_PATHNAMES_HASHES]

    @property
    def _pathname_hash_to_attr(self):
        return self._data[PATHNAME_HASH_TO_ATTRS]

    @property
    def hash_to_pathnames(self):
        return self._data[FILE_HASH_TO_PATHNAMES]

    @property
    def last_update(self):
        return self._data[LAST_UPDATE]

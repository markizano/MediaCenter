#!/usr/bin/env python

import sys, os, json, fnmatch
from pprint import pprint
from configs import configs

class DirectoryListing:
    media_dirs = None
    media_collection = []

    def __init__(self):
        self.media_dirs = os.walk(configs.MEDIA_DIRECTORY)
        if not self.isMediaCacheRecent():
            sys.stdout.write("Media not recently cached; recompiling the index.\n")
            self.gatherMedia()
            self.cacheMedia()
        else:
            self.fetchCache()
            sys.stdout.write("Media recently cached.\n")

    def getMediaCollection(self):
        return self.media_collection

    # Determines the current cache is older than the most recently changed media directory.
    def isMediaCacheRecent(self):
        media_stat = os.stat(configs.MEDIA_DIRECTORY)
        cache_stat = os.stat(configs.CACHE_FILE)

        return media_stat.st_mtime <= cache_stat.st_mtime

    # Gathers the collection of media and returns it in a nice and pretty list.
    def gatherMedia(self):
        for root, dirs, files in self.media_dirs:
            for filename in files:
                for filter_pattern in configs.MEDIA_FILTER_PATTERN:
                    if fnmatch.fnmatch(filename, filter_pattern):
                        try:
                            self.media_collection.append(unicode(os.path.join(root, filename), 'utf-8'))
                        except UnicodeDecodeError, utf:
                            pprint({
                                "error": utf,
                                "tried file": [root, filename]
                            })
        sys.stdout.write("Index compiled.\n")
        return self.media_collection

    def cacheMedia(self):
        fd = open(configs.CACHE_FILE, 'w+')
        json.dump(self.media_collection, fd)
        fd.close()
        return self

    def fetchCache(self):
        fd = open(configs.CACHE_FILE, 'r+')
        self.media_collection = json.load(fd)
        fd.close()
        return self.media_collection



# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
from collections import namedtuple
import unicodedata
import json

if sys.version_info[0] > 2:
    from urllib.parse import unquote
else:
    from urllib import unquote

Source = namedtuple('Source', ['name', 'path'])

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONNAME = ADDON.getAddonInfo('name')
ADDONVERSION = ADDON.getAddonInfo('version')
LANGUAGE = ADDON.getLocalizedString

def log(txt, level=xbmc.LOGDEBUG):
    message = '%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message, level=level)

def jsonrpc(query):
    return json.loads(xbmc.executeJSONRPC(json.dumps(query)))


def _unstack(paths):
    for path in paths:
        if path.startswith("stack://"):
            for part in path.split("stack://", 1)[1].split(" , "):
                # un-escape commas
                yield part.replace(',,', ',')
        else:
            yield path


def _unstack_multipath(path):
    if path.startswith("multipath://"):
        return [unquote(subpath) for subpath in path.split("multipath://")[1].split('/') if subpath]
    return [path]


def _normalize_path(path):
    return path.replace('\\', '/').rstrip('/')


def _normalize_string(name):
    return unicodedata.normalize('NFKD', name).encode('ascii','ignore').decode('utf-8')


def get_movies():
    query = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetMovies",
        "params": {"properties": ["file"]},
        "id": 1
    }
    items = jsonrpc(query)['result'].get('movies', [])
    return list(map(_normalize_path, _unstack((item['file'] for item in items))))


def get_tvshows():
    query = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetTVShows",
        "params": {"properties": ["file"]},
        "id": 1
    }
    items = jsonrpc(query)['result'].get('tvshows', [])
    return [_normalize_path(item['file']) for item in items]


def get_episodes():
    query = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetEpisodes",
        "params": {"properties": ["file"]},
        "id": 1
    }
    items = jsonrpc(query)['result'].get('episodes', [])
    return list(map(_normalize_path, _unstack((item['file'] for item in items))))


def get_sources():
    query = {
        "jsonrpc": "2.0",
        "method": "Files.GetSources",
        "params": {"media": "video"},
        "id": 1
    }
    response = jsonrpc(query)
    sources = []
    for item in response['result'].get('sources', []):
        paths = _unstack_multipath(item['file'])
        for path in paths:
            sources.append(Source(item['label'], _normalize_path(path)))
    return sources


def get_all_sources():
    source_types = [ "video",
                     "music",
                     "pictures",
                     "files",
                     "programs"]
    sources = []
    for source_type in source_types:
        query = {
            "jsonrpc": "2.0",
            "method": "Files.GetSources",
            "params": {"media": "{}".format(source_type)},
            "id": 1
        }
        response = jsonrpc(query)
        for item in response['result'].get('sources', []):
            paths = _unstack_multipath(item['file'])
            for path in paths:
                sources.append(Source(item['label'], _normalize_path(path)))
    return sources


def _identify_source_content():
    movie_content = get_movies()
    tv_content = get_tvshows() + get_episodes()

    movie_sources = []
    tv_sources = []

    new_movie_content = []
    new_tv_content = []

    MediaContent = namedtuple('MediaContent', ['path', 'source'])
    is_movie_source = "false"
    is_tv_source = "false"
    for source in get_sources():
        for m_file_path in movie_content:
            if m_file_path.startswith(source.path + '/'):
                if source not in movie_sources:
                    movie_sources.append(source)
                if MediaContent(m_file_path, source.name ) not in new_movie_content:
                    new_movie_content.append(MediaContent(m_file_path, source.name ))
                is_movie_source = "true"
        for tv_file_path in tv_content:
            if tv_file_path.startswith(source.path + '/'):
                tv_sources.append(source)
                new_tv_content.append(MediaContent(tv_file_path, source.name))
                is_tv_source = "true"
        if is_movie_source == "true":
            is_movie_source = "false"
            log("source '%s' identified as movie source" % source.path)
        elif is_tv_source == "true":
            is_tv_source = "false"
            log("source '%s' identified as tv source" % source.path)
        else:
            log("source '%s' does not contain any known content. "
                          "assuming content not set." % source.path)
    return movie_sources, tv_sources, dict(new_movie_content), dict(new_tv_content)


def get_movie_sources():
    return _identify_source_content()[0]


def get_tv_sources():
    return _identify_source_content()[1]


def get_movie_content():
    return _identify_source_content()[2]


def get_tv_content():
    return _identify_source_content()[3]

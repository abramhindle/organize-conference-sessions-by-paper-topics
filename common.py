#  Copyright (C) 2014 Alex Wilson
#  Copyright (C) 2012 Abram Hindle
#  Copyright (C) 2012 Corey Hunt
#  
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import datetime, itertools, json, os, shlex, shutil, string
import subprocess, sys, tempfile, traceback

from dateutil.parser import parse as _parse_date_str
from dateutil.tz import tzutc

import http


DATE_PATTERN = '%a, %d %b %Y %H:%M:%S %z'

def parse_date_str(date_string):
    '''parses a date string and sets the timzone to tzutc if none is found.

    :returns: a datetime.datetime object'''
    try:
        parsed = _parse_date_str(date_string)
    except BaseException as e:
        err_string = "Failed to parse date '{}' \n {}"
        raise ValueError(err_string.format(date_string, str(e)))

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tzutc())
    return parsed

def utc_now():
    '''returns a timezone-aware datetime object for the current time'''
    return datetime.datetime.utcnow().replace(tzinfo=tzutc())

def safe_decode_str(s):
    '''safely turn a string into utf-8, even if it is cp1252-encoded'''
    try:
        return s.encode('utf-8')
    except UnicodeError:
        return x.decode('cp1252', 'replace').encode('utf-8')

def iter_batches(iterable, size):
    '''split up an iterable into batches.

    :returns: an iterator of lists
    '''
    i = iter(iterable)
    while True:
        batch = list(itertools.islice(i, size))
        if len(batch) == 0:
            raise StopIteration
        yield batch


def file_last_modified(filename):
    '''get the mtime as a timezone aware datetime for a file'''
    mtime = os.path.getmtime(filename)
    mtime = datetime.datetime.fromtimestamp(mtime, tzutc())
    return mtime

def run_command(command):
    '''safely run a command as a subprocess and print out any output or error
        messages it produces.'''
    if type(command) is str:
        command = shlex.split(command)
    try:
        print command
        print subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        print 'failed with return code {}'.format(e.returncode)
        print e.output
        print 'returned {}'.format(e.returncode)
        sys.stdout.flush()
        raise
 

class SimpleRouter(object):
    '''
        Router that routes dynamic urls with a prefix tree.

        Basically, we split the url into parts (by /), and then
        match the first part. If it matches any prefixes exactly,
        we recursively match the rest of the url from there. If it
        doesn't match any prefixes, then we match it to a dynamic part,
        if there is one at this point. Otherwise, the url is unmatched.
    '''

    class Endpoint(object):
        '''An endpoint with a full route and a user-defined thing.
            Usually endpoint would be a method or a function.
        '''
        def __init__(self, route, endpoint):
            '''
                route = list of url parts
                endpoint = probably a function/method

                we need the whole list of parts for this endpoint
                so that we can do keyword matching of args for
                dynamic values.
            '''
            self.endpoint = endpoint

            self.dynamic = []
            for i in range(len(route)):
                if SimpleRouter.is_dynamic_part(route[i]):
                    self.dynamic.append(route[i][1:])
            self.pattern = '/'.join(route)

        def route(self, dynamic_values):
            '''return the dynamic values mapped to the expected names
                and the endpoint'''
            dyn = {}
            for i in range(len(dynamic_values)):
                dyn[self.dynamic[i]] = dynamic_values[i]
            return dyn, self.endpoint
        
    class Prefix(object):
        def __init__(self, route):
            self._route = route
            self.endpoints = {}
            self.subs = {}

        def add_sub(self, parts, endpoint, methods):
            if len(parts) == 0:
                for method in methods:
                    self.endpoints[method] = endpoint
                return

            if parts[0] not in self.subs:
                self.subs[parts[0]] = SimpleRouter.Prefix(parts[0])
            self.subs[parts[0]].add_sub(parts[1:], endpoint, methods)

        def allows(self, path):
            if len(path) == 0:
                return self.endpoints.keys()
            elif path[0] in self.subs:
                return self.subs[path[0]].allows(path[1:])
            elif '$' in self.subs:
                return self.subs['$'].allows(path[1:])
            return []

        def route(self, path, method, dynamic=None):
            '''return the routed endpoint for the path and the given
                dynamic values'''
            dynamic = dynamic or []

            if len(path) == 0:
                if method in self.endpoints:
                    return self.endpoints[method].route(dynamic)
                else:
                    return None, None
            else:
                if path[0] in self.subs:
                    return self.subs[path[0]].route(path[1:], method, dynamic)
                elif '$' in self.subs:
                    dynamic.append(path[0])
                    return self.subs['$'].route(path[1:], method, dynamic)
                else:
                    return None, None

        def list(self):
            '''returns a list of (route, methods, endpoint) pairs'''
            sub_list = list(itertools.chain(*map(lambda x: x.list(),
                self.subs.values())))

            if self.endpoints:
                sub_list.extend([
                    (e.pattern, method, e.endpoint)
                    for method, e in self.endpoints.iteritems()])
            return sub_list

    def __init__(self, base = ''):
        self.prefix = SimpleRouter.Prefix('')
        self.base = base

    def list(self):
        '''returns a list of (route, methods, endpoint) pairs'''
        routes = self.prefix.list()
        return sorted(routes, key=lambda (r, m, e): r)

    def allows(self, path):
        '''
            returns a list of all methods supported by this path.
            [] if there are no handlers for this path.
        '''
        return self.prefix.allows(self.split_path(path))

    def route(self, path, method='GET'):
        '''
            returns (params, endpoint), where
                params: the url parameters by name as expected by the endpoint
                endpoint: the endpoint added using add_route
        '''
        return self.prefix.route(self.split_path(path), method)

    def add_route(self, path, methods=['GET']):
        '''
            use this as a decorator to add routes
            path can contain variables which will be passed by name
            into the view func.

            .. code-block:: python

                >> @router.add_route('/this/is/my/$project/route')
                .. def view_project(project):
                ..      pass

            then ``/this/is/my/awesome/route`` will call
            ``view_project('awesome')``
        '''
        parts = self.split_path(path)
        def wrap(view_func):
            endpoint = SimpleRouter.Endpoint(parts, view_func)
            
            for i in range(len(parts)):
                if SimpleRouter.is_dynamic_part(parts[i]):
                    parts[i] = '$'

            self.prefix.add_sub(parts, endpoint, methods)
            return view_func
        return wrap

    @staticmethod
    def split_path(path):
        return [p for p in path.strip().strip('/').split('/') if len(p) > 0]

    @staticmethod
    def is_dynamic_part(part):
        return len(part) > 0 and part[0] == '$'


class HandlerControllerBase(object):
    @staticmethod
    def static_routes(router, routes):
        for route, filename in routes.items():
            router.add_route(route)(http.serve_static_for_endpoint(filename))
            # use the add_route decorator as a normal function
            # with the function returned by HTMLContent.for_endpoint

    def __init__(self, request, task_queue):
        self.request = request
        self.task_queue = task_queue
        self.urlquery = ""

    def abort(self, code, message):
        '''bail on the current method with an HTTP error'''
        raise http.HTTPError(code, message)

    def clean_query(self, searchterm):
        """this function removes non alphanumeric characters
            from the string it is passed"""
        newSearchTerm = ''
        whitelist = string.letters + string.digits + string.whitespace
        for char in searchterm:
            if char in whitelist:
                newSearchTerm += char
            else:
                newSearchTerm += ' '
        return newSearchTerm

    def command_not_found(self, *args):
        result = "You did not enter a valid command"
        print result, self.request.path
        return result

    def respond(self):
        params, view_func = self.router.route(self.request.path,
                                   self.request.headers['METHOD'])
        params = params or {}
        view_func = view_func or HandlerControllerBase.command_not_found
        print "I should call", view_func
        self.route_resolved(view_func, **params)
        return self.format_response(view_func(self, **params))

    def route_resolved(self, view_func, **kwargs):
        '''hook method called before running a route'''
        pass

    def format_response(self, response):
        return response

    def should_304(self, etag=None, modified=None):
        return http.should_304(self.request, etag, modified)


class TempDir(object):
    '''A python context object that creates and destroys a temporary directory

        .. code-block:: python

            >> with TempDir() as td:
            ..     print td.path
            ..     print td.join('stuff')
            /tmp/asdofj/
            /tmp/asdofj/stuff

    :attr: path: the path of the temp dir
    '''
    def __enter__(self):
        self.path = tempfile.mkdtemp()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(self.path)

    def join(self, *parts):
        '''join a path with the temp dir'''
        return os.path.join(self.path, *parts)


class ChDir(object):
    '''A python context object that changes folders. Eg.

        .. code-block:: python

            >> with ChDir('./some_place'):
            ..     print os.getcwd()
            old_cwd/some_place

            >> print os.getcwd()
            old_cwd
    '''
    def __init__(self, new_dir):
        self.old_dir = os.getcwd()
        self.new_dir = new_dir

    def __enter__(self):
        os.chdir(self.new_dir)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.old_dir)


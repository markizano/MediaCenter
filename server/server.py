#!/usr/bin/env python

import os, sys, socket, json
from pprint import pprint
from configs import configs
from base64 import b64encode
from DirectoryListing import DirectoryListing

class server:

    # Class properties
    connection = None
    client_connection = None
    dir_listing = None

    def __init__(self):
        try:
            self.connection = socket.socket()
            self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except:
            sys.stderr.write("Could not create socket instance\n")
        self.setupConfig()
        self.sanityChecks()
        self.dir_listing = DirectoryListing()
        self.start()
        while True:
            listened = self.listen()
            if not listened: break

    def __del__(self):
        # @TODO Need to do some kind of check for the type of connection that is present.
        # If a connection is present, then SHUT_RDWR, otherwise, SHUT_RD
        if isinstance(self.connection, socket.socket):
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
            except socket.error, exception:
                sys.stderr.write("Socket not cleanly closed: %s.\n" % exception)

    # Checks to make sure all required files exist before attempting to open them later at some point.
    def sanityChecks(self):
        if not os.path.exists(configs.CONFIG_FILE) or not os.path.isfile(configs.CONFIG_FILE):
            os.system("touch -d '1970-01-01' %s" % ("'" + configs.CONFIG_FILE.replace("'", "'\\''") + "'"))
        if not os.path.exists(configs.CACHE_FILE) or not os.path.isfile(configs.CACHE_FILE):
            os.system("touch -d '1970-01-01' %s" % ("'" + configs.CACHE_FILE.replace("'", "'\\''") + "'"))
        return self

    # Reads some sort of configuration file (preferrably XML) and populates this object with that
    # configuration data.
    def setupConfig(self):
        fd = open(configs.CONFIG_FILE, 'r+')
        try:
            config = json.load(fd, 'utf-8')
            if isinstance(config, dict):
                for conf in config:
                    if hasattr(configs, conf):
                        setattr(configs, conf, config[conf])
                    else:
                        sys.stderr.write("Warning: Unrecognized config option: %s.\n" % conf)
        except ValueError, err:
            pprint(err)
            sys.stderr.write("Unable to parse config file as JSON.\n")

        fd.close()

    def start(self):
        sys.stdout.write("Starting server...\n")
        if not isinstance(self.connection, socket.socket):
            sys.stderr.write("Unable to bind socket; Connection handle is not a socket instance!\n")
        try:
            self.connection.bind((configs.BINDING_ADDRESS, configs.BINDING_PORT))
            self.connection.listen(1)
        except:
            sys.stderr.write("Unable to bind to socket.\n")

    # Listens for input and returns the result on the connection
    def listen(self):
        sys.stdout.write("Listening on %s:%d\n" % (configs.BINDING_ADDRESS, configs.BINDING_PORT))
        if not isinstance(self.connection, socket.socket):
            sys.stderr.write("Could not open socket; Connection handle is not a socket instance!\n")

        data = packet = ""
        result = handled = None
        connection, address = self.connection.accept()
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sys.stdout.write("Client connected @%s:%d\n" % address)

        while True:
            packet = connection.recv(1024)
            # If we reach an escape sequence.
            if not packet or packet == "\x04" or packet == "\0": break
            data += packet

        # Attempt to read the data as JSON
        data = data.rstrip("\x04").rstrip("\0").strip()
        if data:
            try:
                result = json.loads(unicode(data, 'utf-8'), 'utf-8')
                #connection.send(json.dumps({'response': {'status': True, 'messages': []}}) + '\n')
            except ValueError, err:
                sys.stderr.write("Unable to parse input as JSON: %s\n" % err)
                connection.send(json.dumps({
                    'response': {
                        'status': False,
                        'messages': ['Error: JSON parse failed: %s' % err]
                    }
                }) + '\n')
                connection.shutdown(socket.SHUT_RDWR)
                connection.close()
                sys.stdout.write("Client ended the stream\n")
                return False

            handled = self.handle(result)
            connection.send(handled + '\n')
        else:
            sys.stdout.write("There was no data to parse.\n")
            connection.send(json.dumps({'response': {'status': True, 'messages': ['Warning: There was no data to parse']}}) + '\n')

        # Cleanly close the client connection socket
        connection.shutdown(socket.SHUT_RDWR)
        connection.close()
        sys.stdout.write("Client ended the stream\n")
        return result

    # Handles a request for data. Handles requests for the directory listing, individual files, and
    # stopping the server.
    def handle(self, request):
        if not isinstance(request, dict):
            raise ValueError("Argument 1 (request) expected dict().")
        if 'request' not in request:
            raise ValueError('Argument 1 (request) must have "request" dict.')
        else:
            request = request['request']
        #pprint(request)
        if "type" in request:
            pprint(request)
            # {request: {type: 'list'}}
            if request['type'] == 'list':
                return json.dumps({
                    'response': {
                        'status': True,
                        'messages': ["Media listing."],
                        'collection': self.dir_listing.getMediaCollection()
                    }
                })
            # {request: {type: 'file', target: '/home/Media/Music/media.wav'}}
            elif request['type'] == 'file':
                if 'target' in request and os.path.exists(request['target']) and request['target'] in self.dir_listing.getMediaCollection():
                    fd = open(request['target'], 'rb')
                    result = json.dumps({
                        'response': {
                            'status': True,
                            'messages': ["Requested media, at your service."],
                            'filename': request['target'],
                            'contents': fd.read()
                        }
                    })

                    # Be sure to garbage collect.
                    fd.close()
                    return result
            # {request: {type: 'quit'}}
            elif request['type'] == 'quit':
                sys.exit(0)
            else:
                return json.dumps({
                    'response': {
                        'status': False,
                        'messages': ["Invalid request type."]
                    }
                })
        else:
            return json.dumps({
                'response': {
                    'status': False,
                    'messages': ['The reqeuest was missing the `type\' parameter. No commands processed.']
                }
            })


if __name__ == '__main__':
    server()


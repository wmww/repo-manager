#!/usr/bin/python3

import sys
import os
import subprocess
import re
import json

verbose = False

def log(msg):
    if verbose:
        print(msg)

class Run:
    def __init__(self, arg_list, stdin_text=None, raise_on_fail=False):
        log('Running `' + ' '.join(arg_list) + '`')
        p = subprocess.Popen(arg_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(stdin_text)
        self.stdout = stdout.decode('utf-8') if stdout != None else ''
        self.stderr = stderr.decode('utf-8') if stderr != None else ''
        self.exit_code = p.returncode
        if raise_on_fail and self.exit_code != 0:
            raise AssertionError(
                '`' + ' '.join(arg_list) + '` exited with code ' + str(self.exit_code) + ':\n' +
                self.stdout + '\n---\n' + self.stderr)

class Repo:
    def __init__(self, base):
        log('Scanning repo at ' + base)
        assert not os.path.islink(base)
        assert os.path.isdir(base)
        assert os.path.isdir(os.path.join(base, '.git'))

    def __str__(self):
        return 'Git repo'

class Link:
    def __init__(self, base):
        log('Scanning link at ' + base)
        base = os.path.normpath(base)
        assert os.path.islink(base)
        self.target = os.path.realpath(base)
        assert self.target != base

    def __str__(self):
        return 'Link to ' + self.target

class Directory:
    def __init__(self, base):
        log('Scanning directory at ' + base)
        assert not os.path.islink(base)
        assert os.path.isdir(base)
        assert not os.path.isdir(os.path.join(base, '.git'))
        self.contents = {}
        for sub in os.listdir(base):
            if not sub.startswith('.'): # ignore hidden files
                self.contents[sub] = scan_path(os.path.join(base, sub))

    def __str__(self):
        result = ''
        for k, v in self.contents.items():
            if result != '':
                result += ',\n'
            result += k + ' {\n' + str(v) + '\n}'
        return result

class File:
    def __init__(self, base):
        log('Scanning file at ' + base)
        assert not os.path.islink(base)
        assert os.path.isfile(base)

    def __str__(self):
        return 'File'

def scan_path(base):
    assert os.path.isabs(base)
    if os.path.islink(base):
        return Link(base)
    elif os.path.isdir(base):
        if os.path.isdir(os.path.join(base, '.git')):
            return Repo(base)
        else:
            return Directory(base)
    elif os.path.isfile(base):
        return File(base)
    else:
        raise RuntimeError('Encountered unknown thing at ' + base)

def get_directory_from_args(args):
    path = '.'
    if args.directory:
        path = args.directory
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise RuntimeError(path + ' is not a directory')
    return path;

def scan_command(args):
    directory = get_directory_from_args(args)
    state = scan_path(directory)
    print(state)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Manage a directory containing git repos')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser('scan', help='Scan a directory and show the results')
    subparser.set_defaults(func=scan_command)
    subparser.add_argument('-d', '--directory', type=str, help='directory to scan, default is current directory')
    args = parser.parse_args()

    if args.verbose:
        verbose = True

    if not hasattr(args, 'func'):
        parser.print_help()
        exit(1)

    try:
        args.func(args)
    except RuntimeError as e:
        print('Error: ' + str(e), file=sys.stderr)


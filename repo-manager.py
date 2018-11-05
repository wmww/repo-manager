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

class MercurialRepo:
    def __init__(self, base):
        assert os.path.isdir(os.path.join(base, '.hg'))
        assert not os.path.islink(base)
        log('Scanned Mercurial repo at ' + base)

    def __str__(self):
        return 'Mercurial repo'

class GitRepo:
    def __init__(self, base):
        assert os.path.isdir(os.path.join(base, '.git'))
        assert not os.path.islink(base)
        log('Scanned Git repo at ' + base)

    def __str__(self):
        return 'Git repo'

class Link:
    def __init__(self, base):
        base = os.path.normpath(base)
        assert os.path.islink(base)
        self.target = os.path.realpath(base)
        assert self.target != base
        log('Scanned link at ' + base)

    def __str__(self):
        return 'Link to ' + self.target

class Directory:
    def __init__(self, base):
        log('Scanning directory at ' + base)
        assert not os.path.islink(base)
        assert os.path.isdir(base)
        log('Scanning directory at ' + base + '...')
        self.contents = {}
        for sub in os.listdir(base):
            if not sub.startswith('.'): # ignore hidden files
                self.contents[sub] = scan_path(os.path.join(base, sub))
        log('... Scanning ' + base + ' done')

    def __str__(self):
        result = ''
        items = list(self.contents.items())
        for i in range(len(items)):
            key, val = items[i]
            indent_a = ' ├╴'
            indent_b = '\n │ '
            if i != 0:
                result += '\n'
            if i == len(items) - 1:
                indent_a = ' └╴'
                indent_b = '\n   '
            v = str(val)
            if not isinstance(val, Directory):
                if v.find('\n') >= 0:
                    indent_b += '  '
                else:
                    indent_b = ': '
            if v:
                v = '\n' + v
                v = v.replace('\n', indent_b)
            result += indent_a + key + v
        return result

class File:
    def __init__(self, base):
        log('Scanning file at ' + base)
        assert not os.path.islink(base)
        assert os.path.isfile(base)

    def __str__(self):
        return 'File'

def scan_path(base):
    for i in [Link, GitRepo, MercurialRepo, Directory, File]:
        try:
            return i(base)
        except AssertionError:
            pass
    raise RuntimeError('Failed to scan ' + base)

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


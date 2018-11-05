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

def scan_git_repo(path):
    return 'Repo'

def scan_directory(base):
    if os.path.isdir(os.path.join(base, '.git')):
        log(base + ' is git repo, getting state')
        return scan_git_repo(base)
    else:
        log('Scanning ' + base)
        result = {}
        for sub in os.listdir(base):
            path = os.path.join(base, sub)
            if os.path.isdir(path) and not sub.startswith('.'):
                contents = scan_directory(path)
                if contents:
                    result[sub] = contents
        if result:
            return result
        else:
            return None

def print_state(state):
    print(state)

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
    state = scan_directory(directory)
    print_state(state)

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
        print('Error: ' + str(e))


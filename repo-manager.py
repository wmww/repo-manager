#!/usr/bin/python3

import sys
import os
import subprocess
import re
import json

verbose = False

class Run:
    def __init__(self, arg_list, stdin_text=None, raise_on_fail=False):
        if verbose:
            print('Running `' + ' '.join(arg_list) + '`')
        p = subprocess.Popen(arg_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(stdin_text)
        self.stdout = stdout.decode('utf-8') if stdout != None else ''
        self.stderr = stderr.decode('utf-8') if stderr != None else ''
        self.exit_code = p.returncode
        if raise_on_fail and self.exit_code != 0:
            raise AssertionError(
                '`' + ' '.join(arg_list) + '` exited with code ' + str(self.exit_code) + ':\n' +
                self.stdout + '\n---\n' + self.stderr)

def scan_directory(path):
    print('I\'m supposed to be scanning \'' + path + '\', but I don\'t know how yet')
    print('Btw, verbose printing is ' + ('on' if verbose else 'off'))

def print_state(state):
    print(state)

def get_directory_from_args(args):
    if args.directory == None:
        return '.'
    else:
        return args.directory

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

    args.func(args)
    

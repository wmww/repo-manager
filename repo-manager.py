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

class Context:
    def __init__(self):
        self.git_repos = 0
        self.mercurial_repos = 0
        self.clean_repos = 0
        self.problem_repos = 0

class Run:
    def __init__(self, arg_list, path=None, stdin_text=None, raise_on_fail=False):
        log('Running `' + ' '.join(arg_list) + '`')
        p = subprocess.Popen(arg_list, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(stdin_text)
        self.stdout = stdout.decode('utf-8') if stdout != None else ''
        self.stderr = stderr.decode('utf-8') if stderr != None else ''
        self.exit_code = p.returncode
        if raise_on_fail and self.exit_code != 0:
            raise AssertionError(
                '`' + ' '.join(arg_list) + '` exited with code ' + str(self.exit_code) + ':\n' +
                self.stdout + '\n---\n' + self.stderr)

def style(s):
    if s:
        return '\x1b[' + s + 'm'
    else:
        return '\x1b[0m'

def style_if(txt, s, cond):
    if cond:
        return style(s) + txt + style(None)
    else:
        return txt

class MercurialRepo:
    def __init__(self, base, ctx):
        assert os.path.isdir(os.path.join(base, '.hg'))
        assert not os.path.islink(base)
        ctx.mercurial_repos += 1
        log('Scanned Mercurial repo at ' + base)

    def __str__(self, color=False):
        return style_if('Mercurial repo', '1;35', color)

class GitRepo:
    def __init__(self, base, ctx):
        assert os.path.isdir(os.path.join(base, '.git'))
        assert not os.path.islink(base)
        log('Scanning Git repo at ' + base + '...')
        status_output = Run(['git', 'status'], path=base, raise_on_fail=True).stdout
        remotes_output = Run(['git', 'remote', '-v'], path=base, raise_on_fail=True).stdout
        self.working_tree_clean = bool(re.findall('nothing to commit, working tree clean', status_output))
        self.has_remotes = bool(re.findall('[^\s]+\s+.+[$\n]', remotes_output))
        self.synced_with_remote = bool(re.findall('Your branch is up to date with \'.*/.*\'\.', status_output))
        ctx.git_repos += 1
        if self.is_problem():
            ctx.problem_repos += 1
        else:
            ctx.clean_repos += 1
        log('... Scanned ' + base + ' done')

    def is_problem(self):
        return not self.working_tree_clean or not self.has_remotes or not self.synced_with_remote

    def __str__(self, color=False):
        result = []
        if not self.working_tree_clean:
            result.append('Working tree dirty')
        if not self.has_remotes:
            result.append('No remotes')
        if not self.synced_with_remote:
            result.append('Not synced with remote')
        if self.is_problem():
            result = ['Git repo'] + result
        else:
            result = ['Clean Git repo'] + result
        if color:
            s = style('1;31') if self.is_problem() else style('1;32')
            for i in range(len(result)):
                result[i] = s + result[i] + style(None)
        return '\n'.join(result)

class Link:
    def __init__(self, base, ctx):
        base = os.path.normpath(base)
        assert os.path.islink(base)
        self.target = os.path.realpath(base)
        assert self.target != base
        log('Scanned link at ' + base)

    def __str__(self, color=False):
        return style_if('Link to ' + self.target, '1;36', color)

class Directory:
    def __init__(self, base, ctx):
        log('Scanning directory at ' + base)
        assert not os.path.islink(base)
        assert os.path.isdir(base)
        log('Scanning directory at ' + base + '...')
        self.contents = {}
        self.contains_git_repo = False
        for sub in os.listdir(base):
            if not sub.startswith('.'): # ignore hidden files
                 scanned = scan_path(os.path.join(base, sub), ctx)
                 if (isinstance(scanned, GitRepo) or
                        (isinstance(scanned, Directory) and
                        scanned.contains_git_repo)):
                    self.contains_git_repo = True
                 self.contents[sub] = scanned
        log('... Scanning ' + base + ' done')

    def __str__(self, color=False):
        if not self.contains_git_repo:
            result = 'Directory without git repos'
            if color:
                result = style('1;34') + result + style(None)
            return result
        # Directories with contents always start with a newline
        result = '\n'
        items = list(self.contents.items())
        for i in range(len(items)):
            key, val = items[i]
            indent_a = ' ├╴'
            indent_b = ' │ '
            if i != 0:
                result += '\n'
            if i == len(items) - 1:
                indent_a = ' ╰╴'
                indent_b = '   '
            indent_b = style_if(indent_b, '37', color)
            v = val.__str__(color=color)
            if isinstance(val, Directory):
                v = ': ' + v.replace('\n', '\n' + indent_b)
            else:
                indent_b += ' ' * len(key)
                if v.find('\n') == -1:
                    v = ': ' + v
                elif len(v) > 1:
                    v = v.split('\n')
                    v = ('\n' + indent_b).join(
                        [style_if('⎧ ' + v[0],  '0', color)] +
                        [style_if('⎪ ' + i,     '0', color) for i in v[1:-1]] +
                        [style_if('⎩ ' + v[-1], '0', color)])
            indent_a = style_if(indent_a, '37', color)
            result += indent_a + key + v
        return result

class File:
    def __init__(self, base, ctx):
        log('Scanning file at ' + base)
        assert not os.path.islink(base)
        assert os.path.isfile(base)

    def __str__(self, color=False):
        return style_if('File', '1;34', color)

def scan_path(base, ctx):
    for i in [Link, GitRepo, MercurialRepo, Directory, File]:
        try:
            return i(base, ctx)
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
    ctx = Context()
    state = scan_path(directory, ctx)
    color = not args.no_color
    print(directory + ': ' + state.__str__(color=color))
    print()
    print(style_if(str(ctx.clean_repos), '1;32', color) + ' clean repos, ', end='')
    if ctx.problem_repos:
        print(style_if(str(ctx.problem_repos), '1;31', color) + ' dirty repos')
    else:
        print(style_if('No dirty repos', '1;32', color))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Manage a directory containing git repos')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    parser.add_argument('--no-color', action='store_true', help='disable colored output')
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


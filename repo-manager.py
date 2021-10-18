#!/usr/bin/python3

# TODO: use standard logging
# TODO: better color management
# TODO: split into multiple files

import sys
import os
import subprocess
import re
import json
from typing import Optional, Any

verbose = False
default_config_path = '~/.config/repo-manager'

def log(msg: str):
    if verbose:
        print(msg)

def log_warning(msg: str):
    print('Warning: ' + msg)

class Context:
    def __init__(self):
        self.git_repos = 0
        self.mercurial_repos = 0
        self.clean_repos = 0
        self.problem_repos = 0

class Run:
    def __init__(self,
        arg_list: list[str],
        path: Optional[str] = None,
        passthrough=False,
        raise_on_fail=False
    ):
        log('Running `' + ' '.join(arg_list) + '`')
        io = None if passthrough else subprocess.PIPE
        p = subprocess.Popen(arg_list, cwd=path, stdout=io, stderr=io)
        stdout, stderr = p.communicate(None)
        self.stdout = stdout.decode('utf-8') if stdout != None else ''
        self.stderr = stderr.decode('utf-8') if stderr != None else ''
        self.exit_code = p.returncode
        if raise_on_fail and self.exit_code != 0:
            raise AssertionError(
                '`' + ' '.join(arg_list) + '` exited with code ' + str(self.exit_code) + ':\n' +
                self.stdout + '\n---\n' + self.stderr)

def style(s: Optional[str]) -> str:
    if s:
        return '\x1b[' + s + 'm'
    else:
        return '\x1b[0m'

def style_if(txt: str, s: str, cond: bool) -> str:
    if cond:
        return style(s) + txt + style(None)
    else:
        return txt

class MercurialRepo:
    def __init__(self, base: str, ctx: Context):
        assert os.path.isdir(os.path.join(base, '.hg'))
        assert not os.path.islink(base)
        ctx.mercurial_repos += 1
        log('Scanned Mercurial repo at ' + base)

    def __str__(self, color: bool = False):
        return style_if('Mercurial repo', '1;35', color)

class GitRepo:
    def __init__(self, base: str, ctx: Context):
        assert os.path.isdir(os.path.join(base, '.git'))
        assert not os.path.islink(base)
        log('Scanning Git repo at ' + base + '...')
        status_output = Run(['git', 'status'], path=base, raise_on_fail=True).stdout
        remotes_output = Run(['git', 'remote', '-v'], path=base, raise_on_fail=True).stdout
        self.working_tree_clean = bool(re.findall(r'nothing to commit, working tree clean', status_output))
        self.remotes = {}
        for match in re.finditer(r'([^\s]+)\s+([^\s]+).*[$\n]', remotes_output):
            self.remotes[match.group(1)] = match.group(2)
        self.synced_with_remote = bool(re.findall(r'Your branch is up to date with \'.*/.*\'\.', status_output))
        if self.working_tree_clean and self.remotes and not self.synced_with_remote:
            log('Checking if last commit is on remote')
            last_commit = Run(['git', 'rev-parse', 'HEAD'], path=base, raise_on_fail=True).stdout.strip()
            remotes_with_last_commit_result = Run(['git', 'branch', '-r', '--contains', last_commit], path=base, raise_on_fail=False);
            if remotes_with_last_commit_result.exit_code == 0 and remotes_with_last_commit_result.stdout.strip() != '':
                self.synced_with_remote = True
        ctx.git_repos += 1
        if self.is_problem():
            ctx.problem_repos += 1
        else:
            ctx.clean_repos += 1
        log('... Scanned ' + base + ' done')

    def is_problem(self) -> bool:
        return not self.working_tree_clean or not self.remotes or not self.synced_with_remote

    def __str__(self, color=False) -> str:
        result = []
        if not self.working_tree_clean:
            result.append('Working tree dirty')
        if not self.remotes:
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
    def __init__(self, base: str, ctx: Context):
        base = os.path.normpath(base)
        assert os.path.islink(base)
        self.target = os.path.realpath(base)
        assert self.target != base
        log('Scanned link at ' + base)

    def __str__(self, color=False) -> str:
        return style_if('Link to ' + self.target, '1;36', color)

class Directory:
    def __init__(self, base: str, ctx: Context):
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

    def __str__(self, color=False) -> str:
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
    def __init__(self, base: str, ctx: Context):
        log('Scanning file at ' + base)
        assert not os.path.islink(base)
        assert os.path.isfile(base)

    def __str__(self, color=False) -> str:
        return style_if('File', '1;34', color)

def scan_path(base: str, ctx: Context):
    for i in [Link, GitRepo, MercurialRepo, Directory, File]:
        try:
            return i(base, ctx)
        except AssertionError:
            pass
    raise RuntimeError('Failed to scan ' + base)

def get_directory_from_args(args, name: str) -> str:
    path = '.'
    if hasattr(args, name) and getattr(args, name) is not None:
        path = getattr(args, name)
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise RuntimeError(path + ' is not a directory')
    return path;

def scan_command(args) -> None:
    directory = get_directory_from_args(args, 'directory')
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

def setup_repo_with_remotes(repo_dir: str, remotes: dict[str, str]):
    preexisting = os.path.exists(repo_dir)
    if not preexisting:
        parent = os.path.dirname(repo_dir)
        assert os.path.exists(parent), parent + ' does not exist'
        remote_url = remotes.get('origin', list(remotes.values())[0])
        log('Cloning ' + remote_url + ' into ' + repo_dir)
        Run(['git', 'clone', remote_url, repo_dir], passthrough=True, raise_on_fail=True)
    parsed = GitRepo(repo_dir, Context())
    found_match = False
    for repo_name, repo_url in parsed.remotes.items():
        for requested_name, requested_url in remotes.items():
            if repo_url == requested_url:
                found_match = True
                break
        if found_match:
            break
    if not found_match:
        raise RuntimeError(
            'None of the remotes in existing repo ' +
            repo_dir +
            ' match match any of the specified remotes: ' +
            ' '.join(remotes.values()))
    for name, url in remotes.items():
        if name not in parsed.remotes or url != parsed.remotes[name]:
            if name in parsed.remotes:
                log('Need to remove remote ' + name + ' with url ' + parsed.remotes[name] + ' so it can be replaced with ' + url)
                Run(['git', 'remote', 'remove', name], path=repo_dir, raise_on_fail=True)
            Run(['git', 'remote', 'add', name, url], path=repo_dir, raise_on_fail=True)
        else:
            log(repo_dir + ' already has remote ' + name + ' with url ' + url)
    if preexisting and not parsed.is_problem():
        Run(['git', 'pull'], passthrough=True, raise_on_fail=False)
    log(repo_dir + ' has been set up with ' + str(len(remotes.items())) + ' remotes')

def setup_repo_exclude(repo_dir: str, exclude: list[str]):
    path = os.path.join(repo_dir, '.git', 'info', 'exclude')
    with open(path, 'r') as f:
        original = f.read()
    section_start = '# <repo-manager>'
    section_end = '# </repo-manager>'
    # list of non-repo-manager bits of the exclude file
    sections = re.split(re.escape(section_start) + r'.*?' + re.escape(section_end), original, flags=re.DOTALL)
    if len(exclude) > 0:
        to_add = [section_start] + exclude + [section_end]
        if len(sections) == 1:
            if not sections[0].endswith('\n\n'):
                to_add.insert(0, '')
            if not sections[0].endswith('\n'):
                to_add.insert(0, '')
            to_add.append('')
        sections.insert(1, '\n'.join(to_add))
    result = ''.join(sections)
    if not result.endswith('\n'):
        result += '\n'
    if result != original:
        log('Exclude file updated')
        with open(path, 'w') as f:
            f.write(result)
    else:
        log('Exclude file unchanged')

def create_symlink(target: str, link: str):
    target = os.path.abspath(target)
    if os.path.exists(link):
        if os.path.islink(link):
            if os.path.abspath(os.readlink(link)) == target:
                log('Leaving ' + link + ' unchanged')
                return
            else:
                log('Removing old link from ' + link + ' to ' + os.readlink(link))
                os.remove(link)
        else:
            raise RuntimeError(link + ' already exists and is not a symlink')
    log('Linking ' + link + ' to ' + target)
    os.symlink(target, link)

def symlink_all(target_dir: str, link_dir: str):
    for item in os.listdir(target_dir):
        if not item.startswith('.'):
            create_symlink(os.path.join(target_dir, item), os.path.join(link_dir, item))

def remove_dead_symlinks(link_dir: str):
    for item in os.listdir(link_dir):
        item_path = os.path.join(link_dir, item)
        if os.path.islink(item_path):
            target = os.readlink(item_path)
            if not os.path.exists(target):
                log('Removing broken symlink ' + item_path + ' (was pointing to ' + target + ')')
                os.remove(item_path)

def assert_type(value: Any, expected_type: Any, value_name: str):
    assert isinstance(value, expected_type), (
        str(value_name) + ' is type ' + str(type(value)) + ' instead of ' + str(expected_type)
    )

class RepoConfig:
    def __init__(self, config_dir: Optional[str], config: Any):
        self.symlink_dir = config_dir
        self.remotes: dict[str, str] = config.pop('remotes', None)
        assert_type(self.remotes, dict, 'remotes')
        for k, v in self.remotes.items():
            assert_type(k, str, 'remote name')
            assert_type(v, str, 'remote URL')
        self.exclude: list[str] = config.pop('exclude', [])
        assert_type(self.exclude, list, 'exclude')
        for i, line in enumerate(self.exclude):
            assert_type(line, str, 'exclude line ' + str(i + 1))
        self.name: str = config.pop('name', os.path.basename(config_dir) if config_dir else None)
        assert self.name, 'name must be specified'
        assert_type(self.name, str, 'name')
        config.pop('//', None)
        assert not config, 'unknown key(s): ' + ', '.join(config.keys())

class ConfigDb:
    def __init__(self) -> None:
        self.repos: dict[str, RepoConfig] = {}

    def add_repo(self, config: RepoConfig):
        assert config.name not in self.repos, 'loaded multiple ' + config.name + ' repos'
        self.repos[config.name] = config

    def load_repo_json(self, path: str):
        log('Loading config from ' + path)
        try:
            with open(path, 'r') as f:
                config = RepoConfig(os.path.dirname(path), json.load(f))
                self.add_repo(config)
        except (json.decoder.JSONDecodeError, AssertionError) as e:
            log_warning('failed to load ' + path + ': ' + str(e))

    def load_repo_list_json(self, path: str):
        log('Loading config from ' + path)
        try:
            with open(path, 'r') as f:
                repos = json.load(f)
                assert_type(repos, list, 'repo list')
                for i, repo in enumerate(repos):
                    try:
                        config = RepoConfig(None, repo)
                        self.add_repo(config)
                    except AssertionError as e:
                        log_warning('failed to repo ' + str(i) + ' from ' + path + ': ' + str(e))
        except (json.decoder.JSONDecodeError, AssertionError) as e:
            log_warning('failed to load ' + path + ': ' + str(e))

    def load_dir(self, path: str):
        log('Loading config from ' + path)
        repo_json_path = os.path.join(path, 'repo.json')
        repo_list_json_path = os.path.join(path, 'repo_list.json')
        if os.path.basename(path) == 'repo.json':
            self.load_repo_json(path)
        elif os.path.basename(path) == 'repo_list.json':
            self.load_repo_list_json(path)
        elif os.path.exists(repo_json_path):
            self.load_repo_json(repo_json_path)
        else:
            if os.path.exists(repo_list_json_path):
                self.load_repo_list_json(repo_list_json_path)
            if os.path.isdir(path):
                for item in os.listdir(path):
                    subpath = os.path.join(path, item)
                    if os.path.isdir(subpath):
                        self.load_dir(subpath)
            else:
                log_warning(path + ' is not a directory')

def setup_command(args) -> None:
    repo_dir = args.target
    parent_dir = os.path.dirname(repo_dir)
    if not os.path.isdir(parent_dir):
        raise RuntimeError(parent_dir + ' is not a directory')
    repo_name = args.repo if args.repo else os.path.basename(repo_dir)
    color = not args.no_color
    db = ConfigDb()
    for path in args.config:
        db.load_dir(os.path.expanduser(path))
    config = db.repos.get(repo_name)
    if config is None:
        raise RuntimeError(style_if(repo_name + ' repository is not known', '1;31', color))
    setup_repo_with_remotes(repo_dir, config.remotes)
    setup_repo_exclude(repo_dir, config.exclude)
    if config.symlink_dir is not None:
        symlink_all(config.symlink_dir, repo_dir)
    remove_dead_symlinks(repo_dir)
    print(style_if(repo_dir + ' set up successfully', '1;32', color))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Manage a directory containing git repos')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    parser.add_argument('--no-color', action='store_true', help='disable colored output')
    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser('scan', help='Scan a directory and show the results')
    subparser.set_defaults(func=scan_command)
    subparser.add_argument('directory', nargs='?', type=str, help='directory to scan, default is current directory')

    subparser = subparsers.add_parser('setup', help='Clone or set up a repo from configuration (see repo-json.md)')
    subparser.set_defaults(func=setup_command)
    subparser.add_argument('-c', '--config', nargs='+', default=[default_config_path], type=str, help='directory that contains a repo.json file, repo_list.json file or other configuration directories')
    subparser.add_argument('-r', '--repo', type=str, help='name of the repository')
    subparser.add_argument('target', type=str, help='directory of the repo to set up')

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

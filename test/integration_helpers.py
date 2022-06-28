from typing import Dict, Union, List, Any, Optional
import os
import subprocess
import re

temp_dir_parent = '/tmp/repo-manager-tests'
temp_dir_home = os.path.join(temp_dir_parent, 'home')
temp_dir_config = os.path.join(temp_dir_parent, 'config')

class SetupCommandBase:
    def run(self) -> None:
        pass

SetupCommand = Union[None, SetupCommandBase, str, List[Union[str, SetupCommandBase]]]

def run_setup_command(command: SetupCommand) -> None:
    if isinstance(command, str):
        subprocess.run(['bash', '-c', command], capture_output=True, check=True)
    elif isinstance(command, SetupCommandBase):
        command.run()
    elif isinstance(command, list):
        for item in command:
            run_setup_command(item)
    elif command is not None:
        assert False

class MkDir(SetupCommandBase):
    def __init__(self, path: str, sub_command: SetupCommand) -> None:
        self.path = path
        self.sub_command = sub_command

    def run(self) -> None:
        os.makedirs(self.path)
        cwd = os.getcwd()
        os.chdir(self.path)
        run_setup_command(self.sub_command)
        os.chdir(cwd)

class InitRepo(SetupCommandBase):
    def run(self) -> None:
        run_setup_command([
            'echo foo > file.txt',
            'git init',
            'git add .',
            'git commit -m initial',
        ])

def project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def delete_recursive(path: str) -> None:
    assert os.path.realpath(path).startswith(temp_dir_parent)
    if os.path.isdir(path) and not os.path.islink(path):
        for item in os.listdir(path):
            delete_recursive(os.path.join(path, item))
        os.rmdir(path)
    else:
        os.remove(path)

def clean_up_test() -> None:
    delete_recursive(temp_dir_parent)

def init_test(home: SetupCommand, config: SetupCommand = None) -> None:
    os.makedirs(temp_dir_parent)
    os.chdir(temp_dir_parent)
    MkDir(temp_dir_home, home).run()
    MkDir(temp_dir_config, config).run()

class Result:
    def __init__(self, stdout: str) -> None:
        self.text = stdout
        self.text_no_color = re.sub(r'\x1b\[[\d;]*m', '', stdout)

    def __repr__(self) -> str:
        return self.text

    def __contains__(self, key):
        return key in self.text_no_color

def run_repo_manager(args: List[str]) -> Result:
    os.chdir(temp_dir_home)
    repo_manager_script = os.path.join(project_root(), 'repo-manager.py')
    full_args = ['python3', repo_manager_script] + args
    result = subprocess.run(full_args, encoding='utf-8', capture_output=True)
    assert result.returncode == 0 and not result.stderr, (
        'stderr output of ' + repr(full_args) +
        ':\n' + result.stderr +
        '\nstdout:\n' + result.stdout +
        '\nexit code: ' + str(result.returncode)
    )
    return Result(result.stdout)

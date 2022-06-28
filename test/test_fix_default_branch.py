from unittest import TestCase
import os

from integration_helpers import *

def current_branch(repo: str) -> str:
    return output_of('git -C ' + repo + ' rev-parse --abbrev-ref HEAD')

def default_upstream(repo: str) -> str:
    return output_of('git -C ' + repo + ' rev-parse --abbrev-ref origin')

def upstream_of_branch(repo: str, branch: str) -> str:
    return output_of('git -C ' + repo + ' rev-parse --abbrev-ref ' + branch + '@{upstream}')

class ScanReposIntegration(TestCase):
    def tearDown(self) -> None:
        clean_up_test()

    def test_does_nothing_if_default_branch_correct(self) -> None:
        init_test([
            MkDir('upstream', [
                InitRepo('main'),
            ]),
            'git clone upstream downstream',
        ])
        #result = run_repo_manager(['fix-default-branch', 'downstream'])
        self.assertEquals(current_branch('downstream'), 'main')
        self.assertEquals(default_upstream('downstream'), 'origin/main')
        self.assertEquals(upstream_of_branch('downstream', 'main'), 'origin/main')

    def test_changes_upstream_branch_if_updated(self) -> None:
        init_test([
            MkDir('upstream', [
                InitRepo('main'),
            ]),
            'git clone upstream downstream',
            InDir('upstream', [
                'git checkout -b xyz',
            ]),
        ])
        result = run_repo_manager(['fix-default-branch', 'downstream'])
        self.assertEquals(current_branch('downstream'), 'main')
        self.assertEquals(default_upstream('downstream'), 'origin/xyz')
        self.assertEquals(upstream_of_branch('downstream', 'main'), 'origin/xyz')

    def test_fixes_correct_branch_if_different_checked_out(self) -> None:
        init_test([
            MkDir('upstream', [
                InitRepo('main'),
            ]),
            'git clone upstream downstream',
            InDir('downstream', [
                'git checkout -b foo',
                'git push -u origin HEAD'
            ]),
            InDir('upstream', [
                'git checkout -b xyz',
            ]),
        ])
        result = run_repo_manager(['fix-default-branch', 'downstream'])
        self.assertEquals(current_branch('downstream'), 'foo')
        self.assertEquals(default_upstream('downstream'), 'origin/xyz')
        self.assertEquals(upstream_of_branch('downstream', 'foo'), 'origin/foo')
        self.assertEquals(upstream_of_branch('downstream', 'main'), 'origin/xyz')

    def test_can_change_default_upstream_branch_if_dirty(self) -> None:
        init_test([
            MkDir('upstream', [
                InitRepo('main'),
            ]),
            'git clone upstream downstream',
            InDir('downstream', [
                'echo blah > a.txt',
            ]),
            InDir('upstream', [
                'git checkout -b xyz',
            ]),
        ])
        result = run_repo_manager(['fix-default-branch', 'downstream'])
        self.assertEquals(current_branch('downstream'), 'main')
        self.assertEquals(default_upstream('downstream'), 'origin/xyz')
        self.assertEquals(upstream_of_branch('downstream', 'main'), 'origin/xyz')

    def test_fixes_branch_with_abnormal_name_if_its_the_only_branch(self) -> None:
        init_test([
            MkDir('upstream', [
                InitRepo('main'),
                'git checkout -b xyz',
            ]),
            'git clone upstream downstream',
            InDir('upstream', [
                'git checkout -b abc',
            ]),
        ])
        result = run_repo_manager(['fix-default-branch', 'downstream'])
        self.assertEquals(current_branch('downstream'), 'xyz')
        self.assertEquals(default_upstream('downstream'), 'origin/abc')
        self.assertEquals(upstream_of_branch('downstream', 'xyz'), 'origin/abc')


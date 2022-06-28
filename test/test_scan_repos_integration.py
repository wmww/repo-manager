from unittest import TestCase
import os

from integration_helpers import *

class ScanReposIntegration(TestCase):
    def tearDown(self) -> None:
        clean_up_test()

    def test_scan_empty_dir(self) -> None:
        init_test(
            home=[]
        )
        result = run_repo_manager(['scan', '.'])
        self.assertIn('0 clean repos, No dirty repos', result)

    def test_scan_multiple_repos(self) -> None:
        init_test([
            MkDir('repo_a', [
                InitRepo(),
            ]),
            MkDir('repo_b', [
                InitRepo(),
            ]),
            'git clone repo_a repo_c'
        ])
        result = run_repo_manager(['scan', '.'])
        self.assertIn('1 clean repos, 2 dirty repos', result)

    def test_scan_clean_repo_without_remotes(self) -> None:
        init_test([
            MkDir('repo_a', [
                InitRepo(),
            ]),
        ])
        result = run_repo_manager(['scan', './repo_a'])
        self.assertNotIn('Working tree', result)
        self.assertIn('No remotes', result)
        self.assertIn('0 clean repos, 1 dirty repo', result)

    def test_scan_dirty_repo(self) -> None:
        init_test([
            MkDir('repo_a', [
                InitRepo(),
                'echo xyz > new_file.txt'
            ]),
        ])
        result = run_repo_manager(['scan', './repo_a'])
        self.assertIn('Working tree dirty', result)
        self.assertIn('0 clean repos, 1 dirty repo', result)

    def test_scan_clean_repo(self) -> None:
        init_test([
            MkDir('source', [
                MkDir('repo_a', [
                    InitRepo(),
                ]),
            ]),
            'git clone ./source/repo_a',
        ])
        result = run_repo_manager(['scan', './repo_a'])
        self.assertIn('Clean Git repo', result)
        self.assertIn('1 clean repos, No dirty repos', result)

    def test_searches_whole_tree(self) -> None:
        init_test([
            MkDir('foo', [
                MkDir('repo_a', [
                    InitRepo(),
                ]),
                MkDir('repo_b', [
                    InitRepo(),
                ]),
                MkDir('bar', [
                    MkDir('baz', [
                        MkDir('repo_c', [
                            InitRepo(),
                        ]),
                    ])
                ])
            ]),
        ])
        result = run_repo_manager(['scan', '.'])
        self.assertIn('0 clean repos, 3 dirty repos', result)

    def test_does_not_get_confused_by_recursive_symlink(self) -> None:
        init_test([
            MkDir('foo', [
                MkDir('repo_a', [
                    InitRepo(),
                ]),
                'ln -s ' + temp_dir_home + '/foo foo_link',
            ]),
        ])
        self.assertTrue(os.path.isdir(os.path.join(temp_dir_home, 'foo', 'foo_link', 'repo_a')))
        result = run_repo_manager(['scan', '.'])
        self.assertIn('0 clean repos, 1 dirty repos', result)

    def test_detects_mercurial_repo(self) -> None:
        init_test([
            MkDir('foo', [
                MkDir('repo_a', [
                    MkDir('.hg', [])
                ]),
            ]),
        ])
        result = run_repo_manager(['scan', '.'])
        self.assertIn('Mercurial repo', result)

    def test_detects_non_repo_things(self) -> None:
        init_test([
            MkDir('foo', [
                MkDir('baz', [
                    InitRepo(),
                ]),
                MkDir('bar', [
                    'touch file1',
                ]),
                'touch file2',
            ]),
        ])
        result = run_repo_manager(['scan', '.'])
        self.assertIn('bar: Directory without repos', result)
        self.assertIn('file2: File', result)
        self.assertNotIn('file1', result)

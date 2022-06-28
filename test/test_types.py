import unittest
import subprocess
import os

import integration_helpers
reset_color = '\x1b[0m'

class Typecheck(unittest.TestCase):
    def test_project_typechecks(self) -> None:
        project_root = integration_helpers.project_root()
        os.chdir(project_root)
        os.environ['MYPY_FORCE_COLOR'] = '1'
        result = subprocess.run(['mypy', project_root], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if result.returncode != 0:
            raise RuntimeError('`$ mypy ' + project_root + '` failed:\n\n' + reset_color + result.stdout)

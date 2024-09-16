import os
import filecmp
import subprocess
import unittest
import decode_8086
from str_util import add_spacing

class TestDecode8086(unittest.TestCase):
    def test_listings(self):
        TESTS_DIR = 'tests'
        if not os.path.exists(f'{TESTS_DIR}'):
            os.makedirs(f'{TESTS_DIR}')
        if not os.path.exists(f'{TESTS_DIR}/listings'):
            os.makedirs(f'{TESTS_DIR}/listings')
        if not os.path.exists(f'{TESTS_DIR}/out'):
            os.makedirs(f'{TESTS_DIR}/out')
        if not os.path.exists(f'{TESTS_DIR}/recomp'):
            os.makedirs(f'{TESTS_DIR}/recomp')
        listings = os.listdir(f'{TESTS_DIR}/listings')
        binaries : list[str] = []
        for path in listings:
            if len(path.split('.')) > 1:
                pass
            else:
                binaries.append(path)
        binaries.sort()
        for binary in binaries:
            asm = add_spacing(decode_8086.decode_8086(f'{TESTS_DIR}/listings/{binary}'))
            decode_8086.write_to_file(asm,f'{TESTS_DIR}/out/test_{binary}.asm')
            with subprocess.Popen(f'nasm {TESTS_DIR}/out/test_{binary}.asm -o {TESTS_DIR}/recomp/test_{binary} -w-prefix-lock-xchg', shell=True, stdout=subprocess.PIPE) as proc:
                proc.stdout.read()
                self.assertTrue(filecmp.cmp(f'{TESTS_DIR}/recomp/test_{binary}',f'{TESTS_DIR}/listings/{binary}', False),f'{binary} failed check')
            print(binary.ljust(40), "\t: OK")

if __name__ == "__main__":
    unittest.main()
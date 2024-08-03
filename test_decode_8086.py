from os import listdir
import filecmp
import subprocess
import unittest
import decode_8086

class TestDecode8086(unittest.TestCase):

    def test_listings(self):
        listings = listdir('listings')
        binaries = []
        for path in listings:
            if len(path.split('.')) > 1:
                pass
            else:
                binaries.append(path)
        binaries.sort()
        for binary in binaries:
            asm = decode_8086.decode_8086(f'listings/{binary}')
            decode_8086.write_to_file(asm,f'out/test_{binary}.asm')
            with subprocess.Popen(f'nasm out/test_{binary}.asm -o recomp/test_{binary}', shell=True, stdout=subprocess.PIPE) as proc:
                proc.stdout.read()
                self.assertTrue(filecmp.cmp(f'recomp/test_{binary}',f'listings/{binary}', False),f'{binary} failed check')
            print(binary)

if __name__ == "__main__":
    unittest.main()
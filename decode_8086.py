# Anthony Verdi
# 7/26/24
# 8086 MOV instruction decoder
# HW Assignment #1 From Performance-Aware-Programming Course by Casey Muratori

import sys
# OP Codes
MOV_RR = 0b10001000

# Registers
REG_TABLE_W0 = ['al', 'cl', 'dl', 'bl', 'ah', 'ch', 'dh', 'bh']
REG_TABLE_W1 = ['ax', 'cx', 'dx', 'bx', 'sp', 'bp', 'si', 'di']

# Masks
MOD_MASK    =   0b11000000
REG_MASK    =   0b00111000
RM_MASK     =   0b00000111
BIT_MASK_7  =   0b00000010
BIT_MASK_8  =   0b00000001

def decode_8086(file_path):
    with open(file_path,'rb') as file:
        out_str = 'bits 16'
        while True:
            asm = file.read(1)
            if asm == b'':
                break
            out_str += '\n'
            opcode = asm[0] & 0b11111100
            if opcode == MOV_RR:
                d = bool(asm[0] & BIT_MASK_7)
                w = bool(asm[0] & BIT_MASK_8)
                table = REG_TABLE_W0 if w == 0 else REG_TABLE_W1
                byte2 = file.read(1)
                mod = (byte2[0] & MOD_MASK) >> 6
                out_str += "mov "
                if mod == 0b11: # Register mode
                    reg = (byte2[0] & REG_MASK) >> 3
                    rm = byte2[0] & RM_MASK
                    operands = (table[reg],table[rm])
                    if d == 0:
                        operands = operands[::-1]
                    out_str += f'{operands[0]}, {operands[1]}'
                else: # Not register mode
                    pass
        return out_str
                
def write_to_file(str,file_path):
    with open(file_path,'w+') as file:
        file.write(str)      

def main():
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(file_path)
        result = decode_8086(file_path)
        write_to_file(result,'out/out.asm')
        print(result)
    else:
        print("Incorrect number of arguments") 

if __name__ == "__main__":
    main()        


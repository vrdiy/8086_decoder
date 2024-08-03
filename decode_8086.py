# Anthony Verdi
# 8/3/24
# 8086 MOV instruction decoder
# HW Assignment from Performance-Aware-Programming Course by Casey Muratori

import sys

# OP Codes
OP_MOV_REG_MEM_TOFROM_REG = 0b100010
OP_IMM_TO_REG = 0b1011
OP_IMM_TO_REG_MEM = 0b1100011
OP_MEM_TO_ACCUM = 0b1010000
OP_ACCUM_TO_MEM = 0b1010001

# Registers
REG_TABLE_W0 = ['al', 'cl', 'dl', 'bl', 'ah', 'ch', 'dh', 'bh']
REG_TABLE_W1 = ['ax', 'cx', 'dx', 'bx', 'sp', 'bp', 'si', 'di']

# Register/Memory Field Encoding
EFFECTIVE_ADDR = \
[   
    'bx + si',  #000
    'bx + di',  #001
    'bp + si',  #010
    'bp + di',  #011
    'si',       #100
    'di',       #101
    'bp',       #110 (DIRECT ADDRESS SPECIAL CASE IF MOD = 00)
    'bx'        #111
]
# Masks
BIT_7  =   0b10000000
BIT_6  =   0b01000000
BIT_5  =   0b00100000
BIT_4  =   0b00010000
BIT_3  =   0b00001000
BIT_2  =   0b00000100
BIT_1  =   0b00000010
BIT_0  =   0b00000001

MOD_MASK    =   BIT_1 | BIT_0
REG_MASK    =   BIT_2 | BIT_1 | BIT_0
RM_MASK     =   BIT_2 | BIT_1 | BIT_0
IMMREG_MASK =   BIT_2 | BIT_1 | BIT_0

# Returns the two's complement of the given byte
def twos_complement(byte,num_bits):
    if byte >> (num_bits-1) == 0:
        return byte
    return (byte & ((2**(num_bits)-1)>>1)) - 2**(num_bits-1)

def decode_8086(file_path) -> str:
    with open(file_path,'rb') as file:
        out_str = 'bits 16'
        while True:
            byte1 = file.read(1)
            if byte1 == b'':
                break

            # Register/Memory to/from Register
            if (byte1[0] >> 2) == OP_MOV_REG_MEM_TOFROM_REG:
                byte2 = file.read(1)
                d = byte1[0] & BIT_1 # Order of operands
                w = byte1[0] & BIT_0 # Word or byte
                mod = (byte2[0] >> 6) & MOD_MASK
                reg = (byte2[0] >> 3) & REG_MASK
                rm = byte2[0] & RM_MASK
                reg_table = REG_TABLE_W0 if w == 0 else REG_TABLE_W1

                # Memory Mode, no displacement follows*
                if mod == 0b00: 
                    if rm == 0b110: # Direct address
                        disp_bytes = int.from_bytes(file.read(2),'little')
                        operands = (reg_table[reg], f'[{disp_bytes}]')
                    else:
                        operands = (reg_table[reg],f'[{EFFECTIVE_ADDR[rm]}]')

                # Memory Mode, 8-bit displacement follows
                elif mod == 0b01: 
                    disp = twos_complement(int.from_bytes(file.read(1)),8)
                    operands = (reg_table[reg],f'[{EFFECTIVE_ADDR[rm]} {'+'if disp >= 0 else '-'} {abs(disp)}]')

                # Memory Mode, 16-bit displacement follows
                elif mod == 0b10: 
                    disp = twos_complement(int.from_bytes(file.read(2),"little"),16)
                    operands = (reg_table[reg],f'[{EFFECTIVE_ADDR[rm]} {'+'if disp >= 0 else '-'} {abs(disp)}]')

                # Register Mode (no displacement)
                elif mod == 0b11: 
                    operands = (reg_table[reg],reg_table[rm])

                # Swap operands
                if d == 0:
                    operands = operands[::-1]

                 # Remove displacements of 0
                instruction = f'\nmov {operands[0]}, {operands[1]}'.replace(' + 0','')
                out_str += instruction
            
            # Immediate to Register
            elif (byte1[0] >> 4) == OP_IMM_TO_REG:
                w = byte1[0] & BIT_3
                reg = byte1[0] & IMMREG_MASK
                if w == 0:
                    reg_table = REG_TABLE_W0
                    data = int.from_bytes(file.read(1))
                    operands = (reg_table[reg], data)
                else:
                    reg_table = REG_TABLE_W1
                    data = int.from_bytes(file.read(2),'little')
                    operands = (reg_table[reg], data)
                out_str += f'\nmov {operands[0]}, {operands[1]}'

            # Immediate to Register/Memory
            elif (byte1[0] >> 1) == OP_IMM_TO_REG_MEM:
                byte2 = file.read(1)
                w = byte1[0] & BIT_0
                mod = (byte2[0] >> 6) & MOD_MASK
                rm = byte2[0] & RM_MASK
                if mod == 0b00:
                    operand1 = f'[{EFFECTIVE_ADDR[rm]}]'
                    if rm == 0b110:
                        print("not implemented 0b110 in OP_IMM_TO_REG_MEM")
                elif mod == 0b01:
                    disp = twos_complement(int.from_bytes(file.read(1)),8)
                    operand1 = f'[{EFFECTIVE_ADDR[rm]} {'+'if disp >= 0 else '-'} {abs(disp)}]'
                elif mod == 0b10:
                    disp = twos_complement(int.from_bytes(file.read(2),"little"),16)
                    operand1 = f'[{EFFECTIVE_ADDR[rm]} {'+'if disp >= 0 else '-'} {abs(disp)}]'
                elif mod == 0b11:
                    print("Mode 11 in OP_IMM_TO_REG_MEM not implemented")
                    break
                if w == 0:
                    operand2 = f'byte {int.from_bytes(file.read(1))}'
                else:
                    operand2 = f'word {int.from_bytes(file.read(2),"little")}'
                out_str += f'\nmov {operand1}, {operand2}'

            # Memory to Accumulator
            elif (byte1[0] >> 1) == OP_MEM_TO_ACCUM:
                w = byte1[0] & BIT_0
                addr = int.from_bytes(file.read(2),"little")
                if w == 0: # low portion of AX?
                    operands = ('al',f'[{addr}]')
                else:
                    operands = ('ax',f'[{addr}]')
                out_str += f'\nmov {operands[0]}, {operands[1]}'

            # Accumulator to Memory
            elif (byte1[0] >> 1) == OP_ACCUM_TO_MEM:
                w = byte1[0] & BIT_0
                addr = int.from_bytes(file.read(2),"little")
                if w == 0: # low portion of AX?
                    operands = ('al',f'[{addr}]')
                else:
                    operands = ('ax',f'[{addr}]')
                operands = operands[::-1]
                out_str += f'\nmov {operands[0]}, {operands[1]}'

            # Catch unimplemented instructions
            else:
                print('Instruction not recognized:')
                print(f'\t-> {bin(byte1[0])}')
                break

        return out_str
                
def write_to_file(str,file_path):
    with open(file_path,'w+') as file:
        file.write(str)      

def main():
    if len(sys.argv) > 1:
        # get file name with no extension or path
        name = sys.argv[1].split('.')[0]
        name = name.split('/')
        name = name[-1] if len(name) > 1 else name[0]
        file_path = sys.argv[1]
        print(f'\n-> "{file_path}"')
        result = decode_8086(file_path)
        write_to_file(result,f'{name}.asm')
        print('------------------')
        print(result)
        print('------------------')

    else:
        print("Incorrect number of arguments") 

if __name__ == "__main__":
    main()        
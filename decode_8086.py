# Anthony Verdi
# 2024
# 8086 instruction decoder
# Creates binary matching disassemblies
# HW Assignments and Challenges
# from Performance-Aware-Programming Course by Casey Muratori
import sys, os, io
from str_util import add_spacing

OP_GROUP_IMMED = \
[
    'add',  #000        Add
    'or',   #001        Or
    'adc',  #010        Add with carry
    'sbb',  #011        Sub with borrow
    'and',  #100        And
    'sub',  #101        Subtract
    'xor',  #110        Exclusive or
    'cmp',  #111        Compare
]
OP_GROUP_SHIFT = \
[
    'rol',  #000        
    'ror',  #001        
    'rcl',  #010        
    'rcr',  #011        
    'shl',  #100        
    'shr',  #101        
    'ERR',  #110        
    'sar',  #111        
]
OP_GROUP_1 = \
[
    'test',     #000    
    'ERR',      #001    UNUSED
    'not',      #010    
    'neg',      #011    
    'mul',      #100    
    'imul',     #101    
    'div',      #110    
    'idiv',     #111    
]
OP_GROUP_2 = \
[
    'inc',      #000    
    'dec',      #001    
    'call',     #010    
    'call',     #011    
    'jmp',      #100    
    'jmp',      #101    
    'push',     #110    
    'ERR',      #111    UNUSED
]
STR_OPS = {}
STR_OPS[0b1111001] = 'rep'
STR_OPS[0b1010010] = 'movs'
STR_OPS[0b1010011] = 'cmps'
STR_OPS[0b1010111] = 'scas'
STR_OPS[0b1010110] = 'lods'
STR_OPS[0b1010101] = 'stos'
# Load
LOAD_OPS = {}
LOAD_OPS[0b10001101] = 'lea'
LOAD_OPS[0b11000101] = 'lds'
LOAD_OPS[0b11000100] = 'les'

0b11000101
# Jumps
CTRL_TRNSFR_OPS = {}
CTRL_TRNSFR_OPS[0b01110101] = 'jnz'
CTRL_TRNSFR_OPS[0b01110100] = 'je'
CTRL_TRNSFR_OPS[0b01111100] = 'jl'
CTRL_TRNSFR_OPS[0b01111110] = 'jle'
CTRL_TRNSFR_OPS[0b01110010] = 'jb'
CTRL_TRNSFR_OPS[0b01110110] = 'jbe'
CTRL_TRNSFR_OPS[0b01111010] = 'jp'
CTRL_TRNSFR_OPS[0b01110000] = 'jo'
CTRL_TRNSFR_OPS[0b01111000] = 'js'
CTRL_TRNSFR_OPS[0b01111101] = 'jnl'
CTRL_TRNSFR_OPS[0b01111111] = 'jg'
CTRL_TRNSFR_OPS[0b01110011] = 'jnb'
CTRL_TRNSFR_OPS[0b01110111] = 'ja'
CTRL_TRNSFR_OPS[0b01111011] = 'jnp'
CTRL_TRNSFR_OPS[0b01110001] = 'jno'
CTRL_TRNSFR_OPS[0b01111001] = 'jns'
# Loops
CTRL_TRNSFR_OPS[0b11100010] = 'loop'
CTRL_TRNSFR_OPS[0b11100001] = 'loopz'
CTRL_TRNSFR_OPS[0b11100000] = 'loopnz'
CTRL_TRNSFR_OPS[0b11100011] = 'jcxz'
# Registers
REG_TABLE_W0 =  ['al', 'cl', 'dl', 'bl', 'ah', 'ch', 'dh', 'bh']
REG_TABLE_W1 =  ['ax', 'cx', 'dx', 'bx', 'sp', 'bp', 'si', 'di']
SEG_REG =       ['es', 'cs', 'ss', 'ds']

REG_TABLE = [REG_TABLE_W0, REG_TABLE_W1]
OP_GROUP =  [OP_GROUP_1, OP_GROUP_2]
DIRECTION = [-1,1]

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

# Returns signed int from a two's complement notated int
def from_twos_complement(tc_int,num_bits) -> int:
    # Number is positive
    if tc_int >> (num_bits-1) == 0:
        return tc_int
    
    # Number is negative, mask away negative bit
    # Then subtract max value of (num_bits - 1) bits 
    return (tc_int & ((2**(num_bits)-1)>>1)) - 2**(num_bits-1)

def mod_rm_schema(mod : int, rm  : int, file_handle : io.BufferedReader, reg_table : list[str] = None) -> str:
    """
    Handles instructions that use mod and r/m

    :param int mod: The value of mod [0b00 -> 0b11]
    :param int rm: The value of rm [0b000 -> 0b111]
    :param io.BufferedReader file_handle: The handle of the file
    :param list[str] reg_table: Table of registers used, can be None if 
        operation never takes code path (TODO: further investigation)
    :return: A str operand
    :rtype: str
    """
    global g_seg_override_prefix
    operand : str = ''
    # Memory Mode, no displacement follows*
    if mod == 0b00: 
        if rm == 0b110: # Direct address
            disp_bytes = int.from_bytes(file_handle.read(2),'little')
            operand = f'{g_seg_override_prefix}[{disp_bytes}]'
        else:
            operand = f'{g_seg_override_prefix}[{EFFECTIVE_ADDR[rm]}]'

    # Memory Mode, 8-bit displacement follows
    elif mod == 0b01: 
        disp = from_twos_complement(int.from_bytes(file_handle.read(1)),8)
        operand = f'{g_seg_override_prefix}[{EFFECTIVE_ADDR[rm]} {'+'if disp >= 0 else '-'} {abs(disp)}]'

    # Memory Mode, 16-bit displacement follows
    elif mod == 0b10: 
        disp = from_twos_complement(int.from_bytes(file_handle.read(2),'little'),16)
        operand = f'{g_seg_override_prefix}[{EFFECTIVE_ADDR[rm]} {'+'if disp >= 0 else '-'} {abs(disp)}]'

    # Register Mode (no displacement)
    elif mod == 0b11: 
        operand = reg_table[rm]
    g_seg_override_prefix = ''
    return operand

g_seg_override_prefix = ''
def decode_8086(file_path) -> str:

    global g_seg_override_prefix
    with open(file_path,'rb') as file:
        is_locked = False
        out_str = 'bits 16'
        operands : list[str] = ['','']

        while True:
            byte1 = file.read(1)
            if byte1 == b'':
                break
            
            # Set lock
            if (byte1[0] == 0b11110000):
                out_str += '\nlock '
                is_locked = True
                continue

            # Check if special prefix byte
            if (byte1[0] & 0b11100111 == 0b00100110):
                g_seg_override_prefix = f'{SEG_REG[(byte1[0] >> 3) & (BIT_1 | BIT_0)]}:'
                continue
            
            if not is_locked:
                out_str += '\n'
            is_locked = False

            # TEST/XCHG/MOV Register/Memory <-> Register
            if (byte1[0] in range(0b10000100,0b10001011+1)):
                byte2 = file.read(1)
                d = (byte1[0] >> 1) & BIT_0 # Determines direction of operands
                w = byte1[0] & BIT_0 # Word or byte
                mod = (byte2[0] >> 6) & MOD_MASK
                reg = (byte2[0] >> 3) & REG_MASK
                if ((byte1[0] >> 2) & BIT_0) == 0b1:
                    if byte1[0] >> 1 & BIT_0 == 0b1:
                        op = 'xchg'
                        d = 0 # Direction fixed for matching binaries
                    else:
                        op = 'test'
                else:
                    op = 'mov'
                rm = byte2[0] & RM_MASK
                reg_table = REG_TABLE[w]
                operands = [reg_table[reg], mod_rm_schema(mod,rm,file,reg_table)]
                operands = operands[::DIRECTION[d]]
                # Remove displacements of 0
                instruction = f'{op} {operands[0]}, {operands[1]}'.replace(' + 0','')
                out_str += instruction
            
            # MOV Immediate to Register
            elif (byte1[0] >> 4) == 0b1011:
                w = (byte1[0] >> 3) & BIT_0
                reg = byte1[0] & IMMREG_MASK
                reg_table = REG_TABLE[w]
                data = int.from_bytes(file.read(w+1),'little')
                operands = [reg_table[reg], data]
                out_str += f'mov {operands[0]}, {operands[1]}'

            # MOV Immediate to Register/Memory
            elif (byte1[0] >> 1) == 0b1100011:
                byte2 = file.read(1)
                w = byte1[0] & BIT_0
                mod = (byte2[0] >> 6) & MOD_MASK
                rm = byte2[0] & RM_MASK
                operands[0] = mod_rm_schema(mod,rm,file)
                if w == 0:
                    operands[1] = f'byte {int.from_bytes(file.read(1))}'
                else:
                    operands[1] = f'word {int.from_bytes(file.read(2),'little')}'
                out_str += f'mov {operands[0]}, {operands[1]}'

            # MOV SR<->REG/MEM
            elif (byte1[0] & 0b11111101 == 0b10001100):
                d = (byte1[0] >> 1) & BIT_0
                byte2 = file.read(1)
                mod = (byte2[0] >> 6) & MOD_MASK
                sr = (byte2[0] >> 3) & (BIT_1 | BIT_0)
                rm = byte2[0] & RM_MASK
                reg_table = REG_TABLE[0]
                operands = [mod_rm_schema(mod,rm,file,reg_table),SEG_REG[sr]]
                operands = operands[::-DIRECTION[d]]
                out_str += f'mov {operands[0]}, {operands[1]}'

            # TEST Accumulator
            elif (byte1[0] & 0b11111110 == 0b10101000):
                w = byte1[0] & BIT_0
                accs = ['al','ax']
                operands = [accs[w],int.from_bytes(file.read(w+1),'little')]
                out_str += f'test {operands[0]}, {operands[1]}'

            # Memory to Accumulator
            elif (byte1[0] >> 1) == 0b1010000:
                w = byte1[0] & BIT_0
                addr = int.from_bytes(file.read(2),'little')
                res = [f'mov al, [{addr}]',f'mov ax, [{addr}]']
                out_str += res[w]

            # Accumulator to Memory
            elif (byte1[0] >> 1) == 0b1010001:
                w = byte1[0] & BIT_0
                addr = int.from_bytes(file.read(2),'little')
                if w == 0: # low portion of AX?
                    operands = [f'[{addr}]','al']
                else:
                    operands = [f'[{addr}]','ax']
                out_str += f'mov {operands[0]}, {operands[1]}'

            # Immediate with register/memory 
            # 0b100000sw [mod000r/m -> mod111r/m]
            elif (byte1[0] >> 2) == 0b100000:
                byte2 = file.read(1)
                w = byte1[0] & BIT_0
                s = byte1[0] & BIT_1
                mod = (byte2[0] >> 6) & MOD_MASK
                op = OP_GROUP_IMMED[(byte2[0] & (BIT_5 | BIT_4 | BIT_3))>>3]
                rm = byte2[0] & RM_MASK
                reg_table = REG_TABLE[w]
                prefixes = ['byte ','word ']
                operands[0] = mod_rm_schema(mod,rm,file,reg_table)
                operands[1] = prefixes[w]
                if mod == 0b11:
                    operands[1] = ''
                if w == 0:
                    operands[1] += f'{int.from_bytes(file.read(1))}'
                else: # w == 1
                    if s == 0:
                        operands[1] += f'{int.from_bytes(file.read(2),'little')}'
                    else: # s == 1  
                        # Sign extend 8-bit immediate data to 16 bits if w == 1
                        if (mod == 0b00 and rm == 0b110):
                            operands[1] += f'word {int.from_bytes(file.read(1))}'
                        else:
                            operands[1] += f'{int.from_bytes(file.read(1))}'

                out_str += f'{op} {operands[0]}, {operands[1]}'
            
            # Handle OP_GROUP_IMMED (REG_MEM <-> REG_MEM)
            # [0b000000dw -> 0b001110dw]
            elif (byte1[0] & 0b11000100) == 0b0:
                byte2 = file.read(1)
                d = (byte1[0] >> 1) & BIT_0 # Determines direction of operands
                w = byte1[0] & BIT_0 # Word or byte
                op = OP_GROUP_IMMED[(byte1[0] & (BIT_5 | BIT_4 | BIT_3))>>3]
                mod = (byte2[0] >> 6) & MOD_MASK
                reg = (byte2[0] >> 3) & REG_MASK
                rm = byte2[0] & RM_MASK
                reg_table = REG_TABLE[w]
                operands[0] = reg_table[reg]
                operands[1] = mod_rm_schema(mod,rm,file,reg_table)
    
                # Swap operands
                operands = operands[::DIRECTION[d]]

                instruction = f'{op} {operands[0]}, {operands[1]}'.replace(' + 0','')
                out_str += instruction

            # Handle OP_GROUP_IMMED IMM_ACC
            elif (byte1[0] & 0b11000110) == 0b00000100:
                w = byte1[0] & BIT_0 # Word or byte
                op = OP_GROUP_IMMED[(byte1[0] & (BIT_5 | BIT_4 | BIT_3))>>3]
                if w == 0: # low portion of AX?
                    operands = ['al',f'{from_twos_complement(int.from_bytes(file.read(1)),8)}']
                else:
                    operands = ['ax',f'{from_twos_complement(int.from_bytes(file.read(2),'little'),16)}']
                out_str += f'{op} {operands[0]}, {operands[1]}'
            
            # Handle OP_GROUP_SHIFT
            elif (byte1[0] & 0b11111100) == 0b11010000:
                byte2 = file.read(1)
                shift_count = ['1','cl']
                v = (byte1[0] >> 1) & BIT_0
                w = byte1[0] & BIT_0
                mod = (byte2[0] >> 6) & MOD_MASK
                rm = byte2[0] & RM_MASK
                reg_table = REG_TABLE[w]
                op = OP_GROUP_SHIFT[(byte2[0] & (BIT_5 | BIT_4 | BIT_3))>>3]
                operands = [mod_rm_schema(mod,rm,file,reg_table),shift_count[v]]
                prefixes = ['byte ','word ']
                
                if mod == 0b11:
                    out_str += f'{op} {operands[0]}, {operands[1]}'
                else:
                    out_str += f'{op} {prefixes[w]}{operands[0]}, {operands[1]}'.replace(' + 0','')

            # Handle CONTROL TRANSFER
            elif byte1[0] in CTRL_TRNSFR_OPS:
                byte2 = file.read(1)
                disp = from_twos_complement(byte2[0],8)
                disp += 2
                out_str += f'{CTRL_TRNSFR_OPS[byte1[0]]} ${'+'if disp >= 0 else '-'}{abs(disp)}'

            # Handle string ops
            elif byte1[0] >> 1 in STR_OPS:
                wz = byte1[0] & BIT_0 # z not used?
                op = STR_OPS[byte1[0] >> 1]
                suffix = ['b','w']
                if op == 'rep':
                    byte2 = file.read(1)
                    if byte2[0] >> 1 in STR_OPS:
                        op2 = STR_OPS[byte2[0] >> 1]
                        w = byte2[0] & BIT_0 
                        out_str += f'rep {op2}{suffix[w]}'
                    else:
                        print("Tried to use rep with non-string op")
                        break
                else:
                    out_str += f'{op}{suffix[wz]}'

            # Handle OP_GROUP_1 and OP_GROUP_2 + pop
            # Register/memory
            elif ((byte1[0] & 0b11110110) == 0b11110110) or byte1[0] == 0b10001111:
                byte2 = file.read(1)
                w = byte1[0] & BIT_0
                mod = (byte2[0] >> 6) & MOD_MASK
                rm = byte2[0] & RM_MASK
                reg_table = REG_TABLE[w]
                op = OP_GROUP[(byte1[0]>>3) & 0b1][(byte2[0] & (BIT_5 | BIT_4 | BIT_3))>>3]
                prefixes = ['byte ','word ']
                operands = [mod_rm_schema(mod,rm,file,reg_table),'']

                if op == 'call' or op == 'jmp':
                    if byte2[0] >> 3 & 0b1: # far
                        operands[0] = 'far ' + operands[0]
                    prefixes = ['','']

                # Handle Special cases
                if op == 'test': # special case for test
                    operands[1] = f', {int.from_bytes(file.read(w+1),'little')}'

                # Pop works the same but doesn't have share the op code pattern
                if byte1[0] == 0b10001111:
                    op = 'pop'
                if mod == 0b11:
                    out_str += f'{op} {operands[0]}{operands[1]}'
                else:
                    out_str += f'{op} {prefixes[w]}{operands[0]}{operands[1]}'.replace(' + 0','')

            # INC/DEC/PUSH/POP Register
            elif (byte1[0] >> 3) in range(8,12):
                ops = ['inc','dec','push','pop']
                op = ops[(byte1[0] >> 3)-8]
                out_str += f'{op} {REG_TABLE_W1[byte1[0] & REG_MASK]}'

            # CALL Direct Intersegment
            elif (byte1[0] == 0b10011010):
                operands = [int.from_bytes(file.read(2),'little'),int.from_bytes(file.read(2),'little')]
                out_str += f'call {operands[1]}:{operands[0]}'

            # JMP Direct Intersegment
            elif (byte1[0] == 0b11101010):
                operands = [int.from_bytes(file.read(2),'little'),int.from_bytes(file.read(2),'little')]
                out_str += f'jmp {operands[1]}:{operands[0]}'

            # JMP Direct within segment
            elif (byte1[0] == 0b11101001):
                inc_16 = int.from_bytes(file.read(2),'little')
                disp = from_twos_complement(inc_16,16)
                disp += 3
                out_str += f'jmp ${'+'if disp >= 0 else '-'}{abs(disp)}'

            # CALL Direct within segment
            elif (byte1[0] == 0b11101000):
                inc_16 = int.from_bytes(file.read(2),'little')
                disp = from_twos_complement(inc_16,16)
                disp += 3
                out_str += f'call ${'+'if disp >= 0 else '-'}{abs(disp)}'

            # RET Intersegment adding immediate to SP
            elif (byte1[0] == 0b11001010):
                out_str += f'retf {int.from_bytes(file.read(2),'little')}'
            
            # push cs
            elif (byte1[0] == 0b00001110):
                out_str += f'push cs'

            # pop ds
            elif (byte1[0] == 0b00011111):
                out_str += f'pop ds'
          
            # NOP
            elif byte1[0] == 0b10010000:
                out_str += f'nop ;== xchg ax, ax'

            # XCHG Register with accumulator
            elif byte1[0] in range(0b10010001,0b10010111+1):
                out_str += f'xchg ax, {REG_TABLE_W1[byte1[0]& 0b111]}'

            # IN/OUT IMMED8
            elif byte1[0] in range(0b11100100,0b11100111+1):
                al_ax = ['al','ax']
                in_out = ['in','out']
                operands = [al_ax[byte1[0] & 0b1], int.from_bytes(file.read(1))]
                op = in_out[(byte1[0] >> 1) & BIT_0]
                operands = operands[::-DIRECTION[(byte1[0]>>1) & BIT_0]]
                out_str += f'{op} {operands[0]}, {operands[1]}'
            
            # IN/OUT DX
            elif byte1[0] in range(0b11101100,0b11101111+1):
                al_ax = ['al','ax']
                in_out = ['in','out']
                operands = [al_ax[byte1[0] & 0b1], 'dx']
                op = in_out[(byte1[0] >> 1) & BIT_0]
                operands = operands[::-DIRECTION[(byte1[0]>>1) & BIT_0]]
                out_str += f'{op} {operands[0]}, {operands[1]}'
            
            # XLAT
            elif byte1[0] == 0b11010111:
                out_str += f'xlat'

            # LOAD_OPS
            elif byte1[0] in LOAD_OPS:
                byte2 = file.read(1)
                mod = (byte2[0] >> 6) & MOD_MASK
                reg = (byte2[0] >> 3) & REG_MASK
                rm = byte2[0] & RM_MASK
                op = LOAD_OPS[byte1[0]]
                operands[0] = REG_TABLE_W1[reg]
                operands[1] = mod_rm_schema(mod,rm,file,reg_table)
                # Remove displacements of 0
                instruction = f'{LOAD_OPS[byte1[0]]} {operands[0]}, {operands[1]}'.replace(' + 0','')
                out_str += instruction

            elif byte1[0] == 0b11000010: # RET IMMED16(intraseg)
                imm = from_twos_complement(int.from_bytes(file.read(2),'little'),16)
                out_str += f'ret {imm}'
            elif byte1[0] == 0b11000011: # RET (intrasegment)
                out_str += f'ret'
            elif byte1[0] == 0b11001011: # RET (intersegment)
                out_str += f'retf'
            elif byte1[0] == 0b10011111: # LAHF
                out_str += f'lahf'
            elif byte1[0] == 0b10011110: # SAHF
                out_str += f'sahf'
            elif byte1[0] == 0b10011100: # PUSHF
                out_str += f'pushf'
            elif byte1[0] == 0b10011101: # POPF
                out_str += f'popf'
            elif byte1[0] == 0b00110111: # AAA
                out_str += f'aaa'
            elif byte1[0] == 0b00100111: # DAA
                out_str += f'daa'
            elif byte1[0] == 0b00111111: # AAS
                out_str += f'aas'
            elif byte1[0] == 0b00101111: # DAS
                out_str += f'das'
            elif byte1[0] == 0b11010100: # AAM
                byte2 = file.read(1) # Not used?
                out_str += f'aam'
            elif byte1[0] == 0b11010101: # AAD
                byte2 = file.read(1) # Not used?
                out_str += f'aad'
            elif byte1[0] == 0b10011000: # CBW
                out_str += f'cbw'
            elif byte1[0] == 0b10011001: # CWD
                out_str += f'cwd'
            elif byte1[0] == 0b11001100: # INT 3
                out_str += f'int3'
            elif byte1[0] == 0b11001101: # INT IMMED
                out_str += f'int {int.from_bytes(file.read(1))}'
            elif byte1[0] == 0b11001110: # INTO
                out_str += f'into'
            elif byte1[0] == 0b11001111: # IRET
                out_str += f'iret'
            elif byte1[0] == 0b10011011: # WAIT
                out_str += f'wait'
            elif byte1[0] == 0b11111000: # CLC
                out_str += f'clc'
            elif byte1[0] == 0b11110100: # HLT
                out_str += f'hlt'
            elif byte1[0] == 0b11110101: # CMC
                out_str += f'cmc'
            elif byte1[0] == 0b11111010: # CLI
                out_str += f'cli'
            elif byte1[0] == 0b11111001: # STC
                out_str += f'stc'
            elif byte1[0] == 0b11111011: # STI
                out_str += f'sti'
            elif byte1[0] == 0b11111100: # CLD
                out_str += f'cld'
            elif byte1[0] == 0b11111101: # STD
                out_str += f'std'
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
        print(f'-> "{file_path}"')
        result = decode_8086(file_path)
        result = add_spacing(result)
        if not os.path.exists('out'):
            os.makedirs('out')
        write_to_file(result,os.path.join('out/'f'{name}.asm'))
        print('------------------')
        print(result)
        print('------------------')
        print(f'Output written to -> {'out/'f'{name}.asm'}')
    else:
        print('\n-> USAGE: python decode_8086.py <FILE_NAME>') 

if __name__ == "__main__":
    main()        
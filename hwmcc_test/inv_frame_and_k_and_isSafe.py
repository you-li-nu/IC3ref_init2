from pycryptosat import *
import sys
import os
import subprocess
import re

from hwmcc import _read_optional, run_foreground, write_file_print



def main():

    file_path = "/home/li/Documents/IC3ref_init/example/hwmcc17-single-benchmarks"
    # IC3_path = '/home/li/Documents/IC3ref_init2/IC3'
    IC3_path = '/home/li/Documents/IC3ref/IC3'

    args = [IC3_path, '-s']

    result = open("data/IC3_IF_17.txt", "w")

    for subdir, dirs, files in os.walk(file_path):
        for file in files:
            aig_file = subdir + os.sep + file
            if not aig_file.endswith(".aig") and not aig_file.endswith(".aag"):
                continue

            # if "bobmiterbm1or.aig" not in aig_file: continue

            write_file_print(result, aig_file, ',')

            output = run_foreground(args, f_in=aig_file, timeout_seconds=60)

            if output == -1:
                write_file_print(result, "timeout", '\n')
                continue


            inv_frame = parse_inv_frame(output)
            k_value = parse_k(output)

            write_file_print(result, inv_frame, ',')
            write_file_print(result, k_value, ',')
            # Last character is 1 if a counterexample is found. Is 0 if the model is safe.
            write_file_print(result, output[-2], '\n')

            continue


            # if len(output) == 2 and output[0] == '1':
            #     write_file_print(result, "unsafe by initial checking.", '\n')
            #     continue

            latch_list = parse_all_symbol_list(output, 'latch')
            input_list = parse_all_symbol_list(output, 'input')
            rep_list = parse_all_symbol_list(output, 'rep')

            symbol_list = ['null'] + list(latch_list) + list(input_list) + list(rep_list)
            symbol_dict = {symbol_list[i]: i for i in range(1, len(symbol_list))}

            # print(symbol_list)
            # print(symbol_dict)

            # symbol_list, symbol_dict = parse_symbol_list(output)
            border_clauses = parse_border_cubes(output)
            error_clauses = parse_error(output)

            inv_frame = parse_inv_frame(output)
            k_value = parse_k(output)

            write_file_print(result, inv_frame, ',')
            write_file_print(result, k_value, '\n')



def symbol2lit(symbol, symbol_dict):
    if symbol[0] == '~':
        return 0 - symbol_dict[symbol[1:]]
    else:
        return symbol_dict[symbol]


def parse_border_cubes(in_str: str):
    clauses = []
    for line in re.findall(r"border_cube:(.*?)\n", in_str):
        clauses.append(list(map(reverse_lit, line.strip().split(' '))))
    return clauses


def parse_error(in_str: str):
    clauses = []
    segment = re.findall(r"load_error_starts(.*?)load_error_ends", in_str, re.DOTALL)[0]
    for line in segment.split('\n'):
        if line.startswith("Error:") or len(line) == 0: continue
        clauses.append(line.strip().split())
    return clauses

def parse_all_symbol_list(in_str: str, category: str):
    try:
        ans = []
        segment = re.findall(category + r"_list_starts(.*?)" +  category + "_list_ends", in_str, re.DOTALL)[0]
        for line in segment.split('\n'):
            if len(line) == 0: continue
            ans.append(line.strip())
        return ans
    except:
        return []


def parse_inv_frame(in_str: str):
    try:
        return int(re.findall(r"invariant Frame:(.*?)\n", in_str)[0])
    except:
        return -1

def parse_k(in_str: str):
    try:
        return int(re.findall(r"\. K:(.*?)\n", in_str)[-1])
    except:
        return -1

# def parse_symbol_list(in_str: str):
#     symbol_list = ['null']
#     symbol_dict = {}
#
#     # print("=========latch")
#     latch_list = parse_all_symbol_list(output, 'latch')
#     # print("=========input")
#     input_list = parse_all_symbol_list(output, 'input')
#     # print("=========rep")
#     rep_list = parse_all_symbol_list(output, 'rep')
#
#     symbol_list += list(latch_list)
#
#     segment = re.findall(r"symbol_list_starts(.*?)symbol_list_ends", in_str, re.DOTALL)[0]
#     for line in segment.split('\n'):
#         if len(line) == 0: continue
#         symbol_list.append(line.strip())
#         symbol_dict[line.strip()] = len(symbol_list) - 1
#     print(symbol_dict)
#     return symbol_list, symbol_dict


def reverse_lit(lit: str):
    if lit[0] == '~':
        return lit[1:]
    else:
        return '~' + lit


def generate_abc_command(init, aig_file):
    command = ""
    command += "read_aiger " + aig_file + "\n"
    command += "init -S " + init + "\n"
    command += "pdr" + "\n"
    return command

def run_abc_checking(init, aig_file):
    path = '/home/li/Documents/IC3ref_init/example/kaiyu/abc/abc'
    command_file = 'command_file.txt'
    commands = generate_abc_command(init, aig_file)
    f = open(command_file, "w")
    f.write(commands)
    f.close()

    stdin = open(command_file, "r")
    proc = subprocess.Popen(path, stdin=stdin, stdout=subprocess.PIPE, shell=True)
    output = proc.stdout.readlines()
    # print(output[-3])
    # print(output[-2])
    print(output)
    proc.kill()




if __name__ == '__main__':
    main()
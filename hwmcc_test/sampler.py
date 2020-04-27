from pycryptosat import *
import sys
import os
import subprocess
import re

from hwmcc import _read_optional, run_foreground



def main():

    #file_path = '/home/li/Documents/IC3ref_init/example/kaiyu/'
    #file_name = 'shift_multi.aig'
    file_path = "/home/li/Documents/IC3ref_init/example/hwmcc17-single-benchmarks/"
    file_name = "texaspimainp01.aig"

    file_path = "/home/li/Documents/IC3ref_init/example/hwmcc19-single-benchmarks/"
    file_name = "aig/goel/opensource/usb_phy/usb_phy.aig"
    IC3_path = '/home/li/Documents/IC3ref_init2/IC3'

    args = [IC3_path, '-b']
    file = file_path + file_name
    output = run_foreground(args, f_in=file, timeout_seconds=60)
    assert output[0] != '-', "No output"

    print(output)
    latch_list = parse_all_symbol_list(output, 'latch')
    input_list = parse_all_symbol_list(output, 'input')
    rep_list = parse_all_symbol_list(output, 'rep')

    symbol_list = ['null'] + list(latch_list) + list(input_list) + list(rep_list)
    symbol_dict = {symbol_list[i]: i for i in range(1, len(symbol_list))}

    print(symbol_list)
    print(symbol_dict)


    # symbol_list, symbol_dict = parse_symbol_list(output)
    border_clauses = parse_border_cubes(output)
    error_clauses = parse_error(output)

    s = Solver()
    for clause in border_clauses:
        s.add_clause(list(map(lambda x: symbol2lit(x, symbol_dict), clause)))
    for clause in error_clauses:
       s.add_clause(list(map(lambda x: symbol2lit(x, symbol_dict), clause)))

    # sat, solution = s.solve()
    # print(sat)
    # print(solution)
    # clause = []
    # init = ""
    # for j, sign in enumerate(solution):
    #     if j == 0:
    #         continue
    #     lit = j if not sign else 0 - j
    #     clause.append(lit)
    #     if sign:#sign means true
    #         init += '1'
    #     else:
    #         init += '0'
    # run_abc_checking(init[:-1], file)


    num_iter = 0
    sat = True
    while True:
        num_iter += 1
        print("Iteration: " + str(num_iter))
        sat, solution = s.solve()
        # print(sat)
        # print(solution)
        if (not sat):
            print("unSAT")
            break
        else:
            print("SAT")
            # return


        clause = []
        init = ""
        for j, sign in enumerate(solution):
            if j == 0:
                continue
            if j == len(latch_list) + 1:
                break
            lit = j if not sign else 0 - j
            clause.append(lit)
            if sign:#sign means true
                init += '1'
            else:
                init += '0'
        run_abc_checking(init[:-1], file)
        s.add_clause(clause)


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
    ans = []
    segment = re.findall(category + r"_list_starts(.*?)" +  category + "_list_ends", in_str, re.DOTALL)[0]
    for line in segment.split('\n'):
        if len(line) == 0: continue
        ans.append(line.strip())
    return ans


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
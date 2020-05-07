from pycryptosat import *
import sys
import os
import subprocess
import re

from hwmcc import _read_optional, run_foreground, write_file_print
from rand_init_sampler import process_abc_output



def main():

    file_path = "/home/li/Documents/IC3ref_init/example/hwmcc17-single-benchmarks/unsafe"
    # IC3_path = '/home/li/Documents/IC3ref_init2/IC3'
    IC3_path = '/home/li/Documents/IC3ref_init2/IC3'

    args = [IC3_path, '-s', '-b']

    result = open("data/test.txt", 'w')

    for subdir, dirs, files in os.walk(file_path):
        for file in files:
            aig_file = subdir + os.sep + file
            if not aig_file.endswith(".aig") and not aig_file.endswith(".aag"):
                continue

            # if "bobmiterbm1or.aig" not in aig_file: continue

            write_file_print(result, aig_file, ',')

            output = run_foreground(args, f_in=aig_file, timeout_seconds=60)
            if output == -1:
                write_file_print(result, "Timeout!!", "\n")
                continue
            elif output is None or len(output) < 1:
                write_file_print(result, "No output", "\n")
                continue
            elif output[0] == '1' and len(output) < 4:
                write_file_print(result, "unsafe for base case.", '\n')
                continue
            assert output[0] != '-', "No output"

            # print(output)

            latch_list = parse_all_symbol_list(output, 'latch')
            input_list = parse_all_symbol_list(output, 'input')
            rep_list = parse_all_symbol_list(output, 'rep')

            symbol_list = ['null'] + list(latch_list) + list(input_list) + list(rep_list)
            symbol_dict = {symbol_list[i]: i for i in range(1, len(symbol_list))}

            # print(symbol_list)
            # print(symbol_dict)

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
            while True:
                num_iter += 1
                sat, solution = s.solve()  # solution is a point in P /\ Frame

                if (not sat):
                    write_file_print(result, "inv_frame_equals_false", '\n')
                    break
                else:
                    write_file_print(result, "inv_frame_OK", ',')


                clause = []
                init = ""
                for j, sign in enumerate(solution):
                    if j == 0:
                        continue
                    if j == len(latch_list) + 1:
                        break
                    lit = j if not sign else 0 - j
                    clause.append(lit)
                    if sign: #sign means true
                        init += '1'
                    else:
                        init += '0'
                output = run_abc_checking(init[:-1], aig_file)
                s.add_clause(clause)

                # print("\n")
                # print("Solution: " + str(solution))
                # print(" (" + str(len(solution)) + ")")
                # print("Init: " + str(init))
                # print(" (" + str(len(init)) + ")")
                # print("Latch: " + str(len(latch_list)))
                # print("Input: " + str(len(input_list)))
                # print("Rep: " + str(len(rep_list)))

                print(output)

                is_safe, _ = process_abc_output(output)
                print(is_safe)
                #
                # if not is_safe:
                #     write_file_print("check OK", "\n")


                break


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

    proc.kill()
    return output




if __name__ == '__main__':
    main()
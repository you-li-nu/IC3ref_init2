import os
import time

from hwmcc import write_file_print, run_foreground

'''
1. IC3_init2 with threshold T to generate output.
    - Input:
        - aig_file
        - threshold
    - Output:
        - Runtime or Timeout: -> CSV
        - Raw String

2. Get IF, K, is_Safe(IC3_init2), P, Symbol list, Fi
    - Input:
        - Raw String from 1
    - Output
        - IF: -> CSV
        - K: -> CSV
        - is_Safe(IC3_init2): -> CSV
        - P
        - Fi
        - Symbol dict
        - IF_samples: 


# 3. Use Python SAT Solver to sample an init from P/\Fi
#     - Input:
#         - P
#         - Fi
#         - Symbol List
#     - Output:
#         - is_IF_False: -> CSV
#         - init: list of string

4. Use ABC to verify if init is Safe or not
    - Input:
        - aig_file
        - init
    - Output:
        - is_safe(ABC): -> CSV
'''
def pipeline():
    folder_path = "/home/li/Documents/IC3ref_init/example/hwmcc17-single-benchmarks/unsafe"
    IC3_path = '/home/li/Documents/IC3ref_init2/IC3'
    result_file = open('result.csv', 'w')

    for aig_file in traversal_folder(folder_path):
        if 'ringp0' not in aig_file: continue


        gen_threshold = 1.0/1.414

        while gen_threshold < 2:
            write_file_print(result_file, aig_file)
            # 1
            gen_threshold *= 1.414

            write_file_print(result_file, '%.4f' % gen_threshold)

            runtime, raw_output = run_IC3(IC3_path, aig_file, gen_threshold)

            if runtime == -1:
                write_file_print(result_file, 'timeout', '\n')
                continue

            assert raw_output is not None, "raw_output is None"
            write_file_print(result_file, runtime)

            # 2
            IF, K, is_safe_IC3 = parse_raw_output1(raw_output)
            # IF: {-1, N^+}
            # K: {-1, N^+}
            # is_safe_IC3: {None (core dumped), True, False}
            write_file_print(result_file, IF)
            write_file_print(result_file, K)
            write_file_print(result_file, is_safe_IC3)
            if is_safe_IC3 is None:
                write_file_print(result_file, 'core dumped', '\n')
                continue

            P, Fi, Symbol_dict = parse_raw_output2(raw_output)
            # print(P)
            # print(Fi)
            # print(Symbol_dict)

            IF_samples = parse_raw_output3(raw_output)
            print(IF_samples)

            write_file_print(result_file, '', '\n')



            # 4

def parse_raw_output3(raw_output: str):
    try:
        import re
        segment = re.findall(r"IF samples starts\.(.*?)IF samples ends\.", raw_output, re.DOTALL)[0]

        IF_samples = []
        for line in segment.split('\n'):
            if len(line) < 2: continue
            IF_samples.append(latches2booleans(line.split(':')[1]))
        return IF_samples
    except Exception as e:
        print(e)
        return None

def latches2booleans(latches: str):
    booleans = []
    for latch in latches.split(' '):
        if latch.startswith('~'):
            booleans.append('0')
        else:
            booleans.append('1')
    return ''.join(booleans)


def parse_raw_output2(raw_output: str):
    from sampling_from_invariant_frame import parse_error, parse_border_cubes, parse_all_symbol_list
    error_clauses = parse_error(raw_output)
    border_cubes = parse_border_cubes(raw_output)

    latch_list = parse_all_symbol_list(raw_output, 'latch')
    input_list = parse_all_symbol_list(raw_output, 'input')
    rep_list = parse_all_symbol_list(raw_output, 'rep')

    symbol_list = ['null'] + list(latch_list) + list(input_list) + list(rep_list)
    symbol_dict = {symbol_list[i]: i for i in range(1, len(symbol_list))}

    return error_clauses, border_cubes, symbol_dict


def parse_raw_output1(raw_output: str):
    from inv_frame_and_k_and_isSafe import parse_inv_frame, parse_k
    IF = parse_inv_frame(raw_output)
    K = parse_k(raw_output)

    if raw_output[-2] == '0':
        is_safe_IC3 = True
    elif raw_output[-2] == '1':
        is_safe_IC3 = False
    elif 'exit_code' in raw_output:
        print(raw_output)
        is_safe_IC3 = None
    else:
        print(raw_output)
        assert False, 'raw_output -2 is not a number!'

    return IF, K, is_safe_IC3


# def parse


def run_IC3(IC3_path, aig_file, gen_threshold, timeout_seconds=60):
    args = [IC3_path, '-s', '-b', '-p', str(gen_threshold)]
    from datetime import datetime
    start_time = datetime.now()
    output = run_foreground(args, f_in=aig_file, timeout_seconds=timeout_seconds)
    runtime = str(datetime.now() - start_time)
    if output == -1:
        return -1, None
    else:
        return runtime, output



def traversal_folder(folder_path):
    for subdir, dirs, files in os.walk(folder_path):
        for file in files:
            aig_file = subdir + os.sep + file
            if not aig_file.endswith(".aig") and not aig_file.endswith(".aag"):
                continue
            yield aig_file

def main():
    pipeline()

if __name__ == '__main__':
    main()
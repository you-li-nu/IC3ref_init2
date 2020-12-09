import os
import time
import sys

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
    folder_path = "/home/kaiyu/Documents/IC3ref_init2/example/hwmcc17-single-benchmarks/unsafe/"
    IC3_path = '/home/kaiyu/Documents/IC3ref_init2/IC3'
    result_file = open('result.csv', 'w')

    for aig_file in traversal_folder(folder_path):
        if 'bj08amba2g4' not in aig_file: continue

        # 0
        # randomly draw samples from the whole latch space, and test if they are safe using abc.
        time_out = 20
        AC_timeout_cnt, AC_correct_cnt = get_AC_rate(aig_file, 1000, time_out)

        # gen_threshold = 1.0/1.414
        gen_threshold = 1.0

        while gen_threshold < 36:
            write_file_print(result_file, aig_file)
            write_file_print(result_file, AC_timeout_cnt)
            write_file_print(result_file, AC_correct_cnt)

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
            if is_base_case_unsafe(raw_output):
                write_file_print(result_file, 'base case unsafe!', '\n')
                continue

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

            skip_IF = False
            IF_samples = parse_raw_output3(raw_output)
            if IF_samples == None:
                write_file_print(result_file, "exception", '\n')
                continue
            if len(IF_samples) == 0:
                write_file_print(result_file, "IF is unSAT", '\n')
                continue

            # 5
            # randomly draw samples from the whole latch space, and test if they overlap with the IF using IC3.

            IF_total_pick, IF_overlap_pick = parse_raw_output4(raw_output)
            write_file_print(result_file, IF_total_pick)
            write_file_print(result_file, IF_overlap_pick)

            # 4
            # draw samples from the IF using IC3. Test if they are safe using abc.

            num_safe, num_timeout, num_unsafe = test_IF_samples_abc(IF_samples, aig_file, time_out)
            write_file_print(result_file, num_safe)
            write_file_print(result_file, num_timeout)
            write_file_print(result_file, num_unsafe)

            write_file_print(result_file, '', '\n')


def get_AC_rate(aig_file, iter_cnt, time_out, file=None, result=None):
    from rand_init_sampler import rand_binary_string, read_aig_latch, run_abc_checking, process_abc_output

    num_latch = read_aig_latch(aig_file)

    timeout_cnt = 0
    correct_cnt = 0
    first = True

    f = None
    if file is not None:
        f = open(file, 'r')

    if result is not None:
        rf = open(result, 'w')

    sys.stdout.write('\n')
    sys.stdout.flush()
    for iter in range(iter_cnt):
        sys.stdout.write('\r%s/%s' % (iter + 1, iter_cnt))
        sys.stdout.flush()

        if timeout_cnt > 3:
            break

        if f:
            init_str = f.readline().strip()
        else:
            init_str = rand_binary_string(num_latch)

        rf.write(init_str)

        finished, output = run_abc_checking(init_str, aig_file, time_out)

        if not finished:
            timeout_cnt += 1
            rf.write('2\n')
            continue

        is_correct, _ = process_abc_output(output)
        if is_correct:
            correct_cnt += 1
            rf.write('0\n')
        else:
            rf.write('1\n')

    if f:
        f.close()
    rf.close()

    print('\r')
    return timeout_cnt, correct_cnt

def parse_raw_output4(raw_output: str):
    import re
    segments = re.findall(r"total picks: (.*?) overlap picks: (.*?)\n", raw_output)
    # print(segments)
    return int(segments[0][0]), int(segments[0][1])


def test_IF_samples_abc(IF_samples, aig_file, time_out):
    from rand_init_sampler import generate_abc_command, run_abc_checking, process_abc_output
    assert(len(IF_samples) == 100)
    num_timeout = 0
    num_unsafe = 0
    for i in range(len(IF_samples)):
        finished, output = run_abc_checking(IF_samples[i], aig_file, time_out)
        if not finished:
            num_timeout += 1
            break
        is_correct, _ = process_abc_output(output)
        if not is_correct:
            num_unsafe += 1

    num_safe = len(IF_samples) - num_timeout - num_unsafe

    return num_safe, num_timeout, num_unsafe




def is_base_case_unsafe(raw_output: str):
    if raw_output[-2] == '1' and len(raw_output) < 50:
        return True
    return False


def parse_raw_output3(raw_output: str):
    try:
        IF_samples = []
        if "not SAT" in raw_output:
            return IF_samples

        import re
        segment = re.findall(r"IF samples starts\.(.*?)IF samples ends\.", raw_output, re.DOTALL)[0]
        for line in segment.split('\n'):
            if len(line) < 2: continue
            IF_samples.append(latches2booleans(line.split(':')[1]))
        return IF_samples
    except Exception as e:
        print(e)
        return None

def latches2booleans(latches: str):
    booleans = []
    latches = latches.strip()
    # print(latches)
    for latch in latches.split(' '):
        if latch.startswith('~'):
            booleans.append('0')
        elif ord(latch[1]) >= ord('0') and ord(latch[1]) <= ord('9'):
            booleans.append('1')
        else:
            print("Weird: " + latch)
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


def run_IC3(IC3_path, aig_file, gen_threshold=1, timeout_seconds=60, args=[]):
    if args == []:
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

from pycryptosat import *
import sys
import os
import subprocess
import re

from hwmcc import _read_optional, run_foreground, write_file_print



def main():

    #file_path = '/home/li/Documents/IC3ref_init/example/kaiyu/'
    #file_name = 'shift_multi.aig'
    file_path = "/home/li/Documents/IC3ref_init/example/hwmcc19-single-benchmarks/"
    # file_name = "aig/goel/opensource/usb_phy/usb_phy.aig"


    result = open("data/AC_19.txt", "w")

    for subdir, dirs, files in os.walk(file_path):
        for file in files:
            aig_file = subdir + os.sep + file
            # aig_file = "/home/li/Documents/IC3ref_init/example/hwmcc17-single-benchmarks/6s342rb122.aig"
            if not aig_file.endswith(".aig") and not aig_file.endswith(".aag"):
                continue

            result.write(aig_file + ',')
            print(aig_file, end=',')

            num_latch = read_aig_latch(aig_file)
            if num_latch == -1:
                result.write('Unsupported AIG format!\n')
                print('Unsupported AIG format!')
                continue
            if num_latch > 3000:
                result.write('Too many latches!' + str(num_latch) + '\n')
                print('Too many latches!' + str(num_latch))
                continue

            iter_cnt = 100
            correct_cnt = 0
            time_out = 10
            first = True
            for _ in range(iter_cnt):

                init_str = rand_binary_string(num_latch)
                if iter_cnt == 0:
                    init_str = '0' * num_latch
                finished, output = run_abc_checking(init_str, aig_file, time_out)
                if not finished:
                    result.write('timeout\n')
                    print('timeout')
                    break

                is_correct, _ = process_abc_output(output)
                if iter_cnt == 0:
                    first = is_correct
                if is_correct:
                    correct_cnt += 1
            else:
                result.write(str(correct_cnt) + ',' + str(iter_cnt) + ',' + str(first) + '\n')
                print(str(correct_cnt) + ',' + str(iter_cnt) + ',' + str(first))

    result.close()

def read_aig_latch(filename):
    aig_file = open(filename, "rb")
    line = aig_file.readline()
    aig_file.close()
    vars = line.split()
    if len(vars) > 7:
        return -1
    else:
        return int(vars[3].decode())


def rand_binary_string(n):
    import random
    from datetime import datetime
    random.seed(datetime.now())

    s = ""
    for _ in range(n):
        s += str(random.randint(0, 1))
    return s


def generate_abc_command(init, aig_file):
    command = ""
    command += "read_aiger " + aig_file + "\n"
    command += "init -S " + init + "\n"
    command += "pdr" + "\n"
    return command


def run_abc_checking(init, aig_file, timeout):
    path = '/home/li/Documents/IC3ref_init/example/kaiyu/abc/abc'
    command_file = 'command_file.txt'
    commands = generate_abc_command(init, aig_file)
    f = open(command_file, "w")
    f.write(commands)
    f.close()

    stdin = open(command_file, "r")
    proc = subprocess.Popen(path, stdin=stdin, stdout=subprocess.PIPE, shell=True)

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired as err: # send SIGINT; otherwise kill and report this part
        from signal import SIGINT
        proc.send_signal(SIGINT)
        proc.kill()
        return False, None

    output = proc.stdout.readlines()
    proc.kill()

    return True, output

'''
return (false, n): "was asserted in frame n": the model is unsafe
return (true, k): "Verification of invariant with k clauses was successful": the model is safe
'''
def process_abc_output(s):
    if b"was asserted in frame" in s[-2]:
        line = s[-2].decode()
        n = re.findall(r"was asserted in frame (.*?)\.", line)[0]
        return False, int(n)
    elif b"Verification of invariant with" in s[-3]:
        line = s[-3].decode()
        k = re.findall(r"Verification of invariant with (.*?) clauses", line)[0]
        return True, int(k)
    else:
        # print(s)
        return None, s
        # assert False, "unknown line in abc output."

    #     return -1
    # elif




if __name__ == '__main__':
    main()
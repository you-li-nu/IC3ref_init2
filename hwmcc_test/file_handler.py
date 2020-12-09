import os
import time
import shutil

from hwmcc import write_file_print, run_foreground
from pipeline import traversal_folder, get_AC_rate
from rand_init_sampler import generate_abc_command, run_abc_checking, process_abc_output, read_aig_latch
from pipeline3 import write_samples
from run_iimc import  run_iimc

'''
use abc to check is a single file is safe
'''
def is_safe_checker():
    raw_path = "/home/kaiyu/Documents/hwmcc_benchmarks/single/"
    timeout_path = "/home/kaiyu/Documents/hwmcc_benchmarks/single_timeout/"
    unsafe_path = "/home/kaiyu/Documents/hwmcc_benchmarks/single_unsafe/"
    safe_path = "/home/kaiyu/Documents/hwmcc_benchmarks/single_safe/"


    # IC3_path = '/home/kaiyu/Documents/IC3ref_init2/IC3'
    result_file = open('single.csv', 'w')
    timeout = 120

    result_cnt = {'timeout': 0, 'unsafe': 0, 'safe': 0}
    for i, aig_file in enumerate(traversal_folder(raw_path)):
        if i % 10 == 0:
            os.system('''ps -ef | grep 'abc' | grep -v grep | cut -c 9-15 | xargs kill -9''')

        _, filename = os.path.split(aig_file)
        start_time = time.time()

        write_file_print(result_file, aig_file)
        finished, output = run_abc_checking(None, aig_file, timeout)
        running_time = time.time() - start_time
        write_file_print(result_file, running_time)

        if not finished:
            result_cnt['timeout'] += 1
            shutil.copyfile(aig_file, timeout_path + os.sep + filename)
            write_file_print(result_file, 'timeout', end='\n')
            continue

        is_correct, _ = process_abc_output(output)

        if not is_correct:
            result_cnt['unsafe'] += 1
            shutil.copyfile(aig_file, unsafe_path + os.sep + filename)
            write_file_print(result_file, 'unsafe', end='\n')
        else:
            result_cnt['safe'] += 1
            shutil.copyfile(aig_file, safe_path + os.sep + filename)
            write_file_print(result_file, 'safe', end='\n')


def write_sample_files():
    file_type = 'single_unsafe'

    folder_path = f"/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/{file_type}"
    sample_path = f"/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/{file_type}_samples"

    result_file_name = f'{file_type}_samples.csv'
    already_list = []
    with open(result_file_name, 'r') as f:
        for line in f:
            if line and line.strip():
                if line.startswith('aig_filename'):
                    continue
                already_list.append(line.split(',')[0])

    result_file = open(f'{file_type}_samples.csv', 'a')

    time_out = 120
    num_samples = 1000

    if not already_list:
        write_file_print(result_file, 'aig_filename, sample_filename, num_latches, num_samples, timeout_cnt, correct_cnt, execution_time', end='\n')

    for i, aig_file in enumerate(traversal_folder(folder_path)):
        if aig_file in already_list:
            continue

        if i % 10 == 1:
            os.system('''ps -ef | grep 'abc' | grep -v grep | cut -c 9-15 | xargs kill -9''')

        start_time = time.time()
        write_file_print(result_file, aig_file)

        _, filename = os.path.split(aig_file)
        sample_file_name = sample_path + os.sep + filename[:filename.rindex('.')] + ".sample"
        result_file_name = sample_path + os.sep + filename[:filename.rindex('.')] + ".result" # timeout: 2, safe: 0, unsafe, 1
        write_file_print(result_file, sample_file_name)

        num_latches = read_aig_latch(aig_file)
        write_file_print(result_file, num_latches)
        write_file_print(result_file, num_samples)

        write_samples(file=sample_file_name, seed=0, num_latches=num_latches, num_samples=num_samples)

        AC_timeout_cnt, AC_correct_cnt = get_AC_rate(aig_file, num_samples, time_out, file=sample_file_name, result=result_file_name)
        write_file_print(result_file, AC_timeout_cnt)
        write_file_print(result_file, AC_correct_cnt)

        write_file_print(result_file, str(time.time() - start_time), end='\n')


def find_shallow_safe():
    file_type = 'single_safe'

    folder_path = f"/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/{file_type}"
    sample_path = f"/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/{file_type}_samples"
    shallow_path = f"/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/{file_type}_shallow"

    result_file_name = f'{file_type}_shallow_{time.strftime("%Y_%b_%d_%H_%M", time.localtime())}.csv'
    result_file = open(result_file_name, 'w')
    write_file_print(result_file, 'file_name, is_shallow, is_timeout, aig_path')

    time_out = 120 * 10

    for i, aig_file in enumerate(traversal_folder(folder_path)):
        _, filename = os.path.split(aig_file)
        sample_file = sample_path + os.sep + filename[:filename.rindex('.')] + ".sample"
        write_file_print(result_file, filename)

        is_shallow, is_timeout = is_shallow_safe(aig_file, sample_file, time_out)

        write_file_print(result_file, is_shallow)
        write_file_print(result_file, is_timeout)

        write_file_print(result_file, aig_file)

        write_file_print(result_file, '', end='\n')

        if is_shallow:
            shallow_file_path = shallow_path + os.sep + filename
            shutil.move(aig_file, shallow_file_path)


def is_shallow_safe(aig_file, sample_file, time_out):
    start_time = time.time()

    iimc_path = '/home/kaiyu/Documents/iimc_ref/iimc'

    args = [iimc_path, '-t', 'fsis', '--sample', sample_file, aig_file]
    has_res, raw_output = run_iimc(aig_file, tactic='fsis', timeout_seconds=time_out, args=args, iimc_path=iimc_path)
    end_time = time.time() - start_time

    # return: is_shallow, is_timeout
    if not has_res:
        return False, True

    if '[FSIS] safe_idx_list: ' in raw_output:
        return False, False
    else:
        return True, False





if __name__ == '__main__':
    # is_safe_checker()
    # write_sample_files()
    find_shallow_safe()
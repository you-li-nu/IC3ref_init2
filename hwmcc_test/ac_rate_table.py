import os
import time
import shutil
import re


from hwmcc import write_file_print, run_foreground
from pipeline import traversal_folder, get_AC_rate, run_IC3
from rand_init_sampler import generate_abc_command, run_abc_checking, process_abc_output, read_aig_latch
from pipeline3 import write_samples
from run_iimc import run_iimc


def write_sample_files():
    file_type = 'single_safe'

    folder_path = f"/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/{file_type}"
    sample_path = f"/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/{file_type}_samples"

    result_file_name = f'{file_type}_ac_rate_{time.strftime("%Y_%b_%d_%H_%M", time.localtime())}.csv'
    result_file = open(result_file_name, 'w')

    time_out = 120 * 10

    write_file_print(result_file, 'aig_name, Sample_Size, IC3_AC_count, IC3_timeout_count, IC3_run_time, FSIS_AC_count, FSIS_timeout_count, FSIS_run_time,  IC3 Union FSIS, IC3 Intersect FSIS, aig_file_name, sample_file_name, IC3_safe_index, FSIS_safe_index', end='\n')

    for i, aig_file in enumerate(traversal_folder(folder_path)):
        _, filename = os.path.split(aig_file)
        sample_file = sample_path + os.sep + filename[:filename.rindex('.')] + ".sample"
        write_file_print(result_file, filename)
        sample_size = 0
        with open(sample_file, 'r') as f:
            for line in f:
                sample_size += 1 if line and line.strip() else 0
        write_file_print(result_file, sample_size)


        #  ./IC3 -s -sample ../hwmcc_benchmarks/classified_benchmarks/single_safe_samples/pj2016.sample < ../hwmcc_benchmarks/classified_benchmarks/single_safe/pj2016.aig

        ic3_ac, ic3_timeout, ic3_run_time, ic3_safe_index_str = get_IC3_AC_rate(aig_file, sample_file, time_out)
        if i % 10 == 9:
            os.system('''ps -ef | grep 'IC3ref_ac_rate/IC3' | grep -v grep | cut -c 9-15 | xargs kill -9''')

        write_file_print(result_file, ic3_ac)
        write_file_print(result_file, ic3_timeout)
        write_file_print(result_file, ic3_run_time)


        # ./iimc -t fsis --sample  ../hwmcc_benchmarks/classified_benchmarks/single_safe_samples/pj2016.sample ../hwmcc_benchmarks/classified_benchmarks/single_safe/pj2016.aig
        fsis_ac, fsis_timeout, fsis_run_time, fsis_safe_index_str = get_fsis_AC_rate(aig_file, sample_file, time_out)
        if i % 10 == 5:
            os.system('''ps -ef | grep '/iimc_ref/iimc' | grep -v grep | cut -c 9-15 | xargs kill -9''')

        write_file_print(result_file, fsis_ac)
        write_file_print(result_file, fsis_timeout)
        write_file_print(result_file, fsis_run_time)

        #
        ic3_safe_index_set = set(ic3_safe_index_str.split(' '))
        fsis_safe_index_set = set(fsis_safe_index_str.split(' '))

        union_size = len(ic3_safe_index_set.union(fsis_safe_index_set))
        intersection_size = len(ic3_safe_index_set.intersection(fsis_safe_index_set))

        write_file_print(result_file, union_size)
        write_file_print(result_file, intersection_size)

        write_file_print(result_file, aig_file)
        write_file_print(result_file, sample_file)

        write_file_print(result_file, ic3_safe_index_str)
        write_file_print(result_file, fsis_safe_index_str)

        write_file_print(result_file, '', end='\n')



def get_IC3_AC_rate(aig_file, sample_file, timeout):
    start_time = time.time()

    ic3_path = '/home/kaiyu/Documents/IC3ref_ac_rate/IC3'
    args = [ic3_path, '-sample', sample_file]

    runtime, raw_output = run_IC3(ic3_path, aig_file, args=args, timeout_seconds=timeout)
    end_time = time.time() - start_time
    if runtime == -1:  # timeout
        return 0, 1, end_time, ''

    find_res = re.search(r'total picks: ([0-9]*?) overlap picks: ([0-9]*?)\n', raw_output)

    start_index = raw_output.index('safe_idx_list: ') + len('safe_idx_list: ')
    end_index = raw_output.index('IF picks ends.')
    safe_pick_str = str(raw_output[start_index:end_index]).strip()

    return find_res.group(2), 0, end_time, safe_pick_str


def get_fsis_AC_rate(aig_file, sample_file, time_out):
    #@TODO Auto Kill iimc in the interation


    start_time = time.time()

    iimc_path = '/home/kaiyu/Documents/iimc_ref/iimc'
    #[FSIS] safe count: 237, total count 1000

    # ./iimc -t fsis --sample  ../hwmcc_benchmarks/classified_benchmarks/single_safe_samples/pj2016.sample ../hwmcc_benchmarks/classified_benchmarks/single_safe/pj2016.aig

    args = [iimc_path, '-t', 'fsis', '--sample', sample_file, aig_file]
    has_res, raw_output = run_iimc(aig_file, tactic='fsis', timeout_seconds=time_out, args=args, iimc_path=iimc_path)
    end_time = time.time() - start_time

    if not has_res:
        return 0, 1, end_time, ''

    find_res = re.search(r'\[FSIS\] safe count: ([0-9]*?), total count ([0-9]*?)\n', raw_output)

    start_index = raw_output.index('[FSIS] safe_idx_list: ') + len('[FSIS] safe_idx_list: ')
    end_index = raw_output.index('[FSIS] safe_idx_list ends.')
    safe_pick_str = str(raw_output[start_index:end_index]).strip()

    return find_res.group(1), 0, end_time, safe_pick_str








if __name__ == '__main__':
    write_sample_files()

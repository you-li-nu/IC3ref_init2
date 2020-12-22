from pipeline import traversal_folder, run_IC3, parse_raw_output1, \
    parse_raw_output2, parse_raw_output3, get_AC_rate, parse_raw_output4, test_IF_samples_abc, write_file_print
from rand_init_sampler import read_aig_latch
import time
import os
from typing import List

'''
Generate result file with abc according to sample file.
'''


def result_file_generator():
    file_type = 'single_safe'

    folder_path = f"/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/{file_type}"
    sample_path = f"/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/{file_type}_samples"

    time_out = 120 * 10
    num_samples = 1000

    for aig_file in traversal_folder(folder_path):

        _, filename = os.path.split(aig_file)
        sample_file_path = sample_path + os.sep + filename[:filename.rindex('.')] + ".sample"
        result_file_path = sample_file_path[:sample_file_path.rindex(".")] + ".result"
        abc_path = "/home/kaiyu/Documents/cba-master/cba"

        if not os.path.exists(result_file_path):
            print(f"Result file does not exist. Create {result_file_path}")
            get_AC_rate(aig_file=aig_file, iter_cnt=num_samples, time_out=time_out, file=sample_file_path,
                        result=result_file_path, abc_path=abc_path)

        os.system(f'''ps -ef | grep '{abc_path}' | grep -v grep | cut -c 9-15 | xargs kill -9''')



if __name__ == '__main__':
    result_file_generator()
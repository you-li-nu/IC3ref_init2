from pipeline import traversal_folder, run_IC3, parse_raw_output1, \
    parse_raw_output2, parse_raw_output3, get_AC_rate, parse_raw_output4, test_IF_samples_abc, write_file_print
from rand_init_sampler import read_aig_latch
import time
import os

'''
Run Init2 to get IV/Frame, and also get the initial sample overlap rate.
 -  edge case: IC3 may unroll and return False before starting our alg. We should record and remove such files.
 
Run Init3: 
 -  inputs: IV/Frame from Init2 
            or None-overlap samples (TODO)
            
Muiti-start:
 -  suppose by running abc, we know a set of states which are safe.
    now we simply choose one point as the init of Init3
    in the next iteration, we choose another which is not covered so far
    TODO: let init3 print out all overlapped samples.
'''
def pipeline3():
    file_type = 'single_safe'

    folder_path = f"/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/{file_type}"
    sample_path = f"/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/{file_type}_samples"

    IC3_init2_path = '/home/kaiyu/Documents/IC3ref_init2/IC3'
    IC3_init3_path = '/home/kaiyu/Documents/IC3ref_init3/IC3'

    result_file_name = f'{file_type}_IC3_init2_{time.strftime("%Y_%b_%d_%H_%M", time.localtime())}.csv'
    result_file = open(result_file_name, 'w')

    time_out = 120 * 10
    num_samples = 1000

    for aig_file in traversal_folder(folder_path):
        if '139463p0.aig' in aig_file: continue

        _, filename = os.path.split(aig_file)
        sample_file = sample_path + os.sep + filename[:filename.rindex('.')] + ".sample"
        write_file_print(result_file, "filename, gen_threshold, runtime(inaccurate), status, IF_frame, K, is_safe, IF_number_safe, IF_number_timeout, IF_number_unsat, Sample_total_pick, Sample_overlap_pick", end='\n')

        gen_threshold = 1

        while gen_threshold <= 16:
            gen_threshold *= 2
            write_file_print(result_file, filename)
            write_file_print(result_file, gen_threshold)

            # 1: run init2
            args = [IC3_init2_path, '-s', '-b', '-p', str(gen_threshold), '-sample', sample_file]
            runtime, raw_output = run_IC3(IC3_init2_path, aig_file, gen_threshold, args=args)
            write_file_print(result_file, str(runtime))

            if runtime == -1:
                write_file_print(result_file, "Timeout Init2", '\n')
                continue

            # 2 IF pick for init 2
            IF, K, is_safe_IC3 = parse_raw_output1(raw_output)

            if is_safe_IC3 is None:
                write_file_print(result_file, 'core dumped', '\n')
                continue

            IF_samples = parse_raw_output3(raw_output)
            if IF_samples is None:
                write_file_print(result_file, "parse IF samples exception", '\n')
                continue

            if len(IF_samples) == 0:
                write_file_print(result_file, "IF is unSAT", '\n')
                continue

            write_file_print(result_file, "init2 status OK")
            write_file_print(result_file, IF) #IV frame
            write_file_print(result_file, K) #total frame
            write_file_print(result_file, is_safe_IC3)


            num_safe, num_timeout, num_unsafe = test_IF_samples_abc(IF_samples, aig_file, time_out)
            write_file_print(result_file, num_safe)
            write_file_print(result_file, num_timeout)
            write_file_print(result_file, num_unsafe)

            # print("num_safe: %s, num_timeout: %s, num_unsafe: %s" % (num_safe, num_timeout, num_unsafe))

            IF_total_pick, IF_overlap_pick = parse_raw_output4(raw_output)
            write_file_print(result_file, IF_total_pick)
            write_file_print(result_file, IF_overlap_pick)
            write_file_print(result_file, '', end='\n')

            # parse safe_idx_list
            start_index = raw_output.index('safe_idx_list: ') + len('safe_idx_list: ')
            end_index = raw_output.index('IF picks ends.')
            ic3_safe_index_str = str(raw_output[start_index:end_index]).strip()
            ic3_safe_index_set = set(ic3_safe_index_str.split(' '))
            curr_ic3_safe_index_set = ic3_safe_index_set
            sample_safe_index_set = parse_result_file(sample_file, aig_file)
            diff_set = sample_safe_index_set - curr_ic3_safe_index_set

            for i, sample_index in enumerate(diff_set):
                if i > 5:
                    break

                # sample_index is the input of init4

            # init3
            for iter in range(2):
                run_Init_2_3_4('init3', aig_file, result_file, sample_file, raw_output, gen_threshold, time_out)


# Cannot handle 2 for now
def run_Init_2_3_4(init_type: str, aig_file_path, result_file, sample_file, prev_raw_output, gen_threshold, time_out):
    _, aig_file_name = os.path.split(aig_file_path)
    write_file_print(result_file, aig_file_name)

    # 3 generate frame file
    P, Fi, Symbol_dict = parse_raw_output2(prev_raw_output)
    frame_file = aig_file_path[:aig_file_path.rindex('.')] + ".frame"

    write_cubes_of_invariant(Fi, frame_file)

    write_file_print(result_file, f'{init_type}_' + str(iter))

    IC3_init_path = {
        'Init3': '/home/kaiyu/Documents/IC3ref_init3/IC3',
        'Init4': '/home/kaiyu/Documents/IC3ref_init4/IC3',
    }[init_type]

    # 4: generate raw_output for init3
    args = [IC3_init_path, '-s', '-b', '-p', str(gen_threshold), '-f', frame_file, '-sample', sample_file]
    runtime, raw_output = run_IC3(IC3_init_path, aig_file_path, gen_threshold, args=args)
    write_file_print(result_file, runtime)

    if runtime == -1:
        write_file_print(result_file, f"Timeout {init_type}", '\n')
        return

    # 5: Init3 runtime information
    IF, K, is_safe_IC3 = parse_raw_output1(raw_output)

    # print("IF: %s, K: %s, is_safe_IC3: %s" % (IF, K, is_safe_IC3))

    if is_safe_IC3 is None:
        write_file_print(result_file, 'core dumped', '\n')
        return

    # 6: draw samples from the IF using IC3. Test if they are safe using abc.
    IF_samples = parse_raw_output3(raw_output)
    if IF_samples == None:
        write_file_print(result_file, "parse IF samples exception", '\n')
        return

    if len(IF_samples) == 0:
        write_file_print(result_file, "IF is unSAT", '\n')
        return

    write_file_print(result_file, f"{init_type} status OK")
    write_file_print(result_file, IF)
    write_file_print(result_file, K)
    write_file_print(result_file, is_safe_IC3)

    num_safe, num_timeout, num_unsafe = test_IF_samples_abc(IF_samples, aig_file_path, time_out)
    write_file_print(result_file, num_safe)
    write_file_print(result_file, num_timeout)
    write_file_print(result_file, num_unsafe)

    # print("num_safe: %s, num_timeout: %s, num_unsafe: %s" % (num_safe, num_timeout, num_unsafe))

    # 7: IF_total_pick: number of samples, IF_overlap_pick: the samples contained in the IF, read from raw_output
    IF_total_pick, IF_overlap_pick = parse_raw_output4(raw_output)
    write_file_print(result_file, IF_total_pick)
    write_file_print(result_file, IF_overlap_pick)
    write_file_print(result_file, '', '\n')


def parse_result_file(sample_file_path: str, aig_file_path: str):
    time_out = 120
    num_samples = 1000

    assert os.path.exists(sample_file_path)
    result_file_path = sample_file_path[:sample_file_path.rindex(".")] + ".result"
    if not os.path.exists(result_file_path):
        print(f"Result file does not exist. Create {result_file_path}")
        get_AC_rate(aig_file=aig_file_path, iter_cnt=num_samples, time_out=time_out, file=sample_file_path, result=result_file_path)

    with open(result_file_path, 'r') as rf:
        if len(rf.readlines()) < num_samples:
            return set()

        sample_safe_index_set = set()

        for cnt, line in enumerate(rf):
            line = line.strip()
            if not line:
                continue
            assert line.endswith("0") or line.endswith("1") or line.endswith("2")
            if line.endswith("0"):
                sample_safe_index_set.add(cnt)

        return sample_safe_index_set


def write_samples(file, num_latches, seed=0, num_samples=1000):
    import random
    random.seed(seed)
    with open(file, 'w') as f:
        for _ in range(num_samples):
            sample = bin(random.getrandbits(num_latches))[2:]
            f.write('0' * (num_latches - len(sample)) + sample + '\n')



def write_cubes_of_invariant(Fi, output_file):
    with open(output_file, "w") as of:
        for l in Fi:
            line = ''
            for lit in l:
                line += ' '
                if lit.startswith('~'):
                    line += lit[1:]
                else:
                    line += '~'
                    line += lit
            line = line.strip()
            line += '\n'
            of.write(line)


def write_cubes_of_samples(samples, output_file):
    with open(output_file, "w") as of:
        for l in Fi:
            line = ''
            for lit in l:
                line += ' '
                if lit.startswith('~'):
                    line += lit[1:]
                else:
                    line += '~'
                    line += lit
            line = line.strip()
            line += '\n'
            of.write(line)



def main():
    pipeline3()

if __name__ == '__main__':
    main()
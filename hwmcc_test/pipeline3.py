from pipeline import traversal_folder, run_IC3, parse_raw_output1, \
    parse_raw_output2, parse_raw_output3, get_AC_rate, parse_raw_output4, test_IF_samples_abc, write_file_print
from rand_init_sampler import read_aig_latch
import time
import os
import random
from typing import List

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

    result_file_name = f'{file_type}_IC3_init2_3_4_{time.strftime("%Y_%b_%d_%H_%M", time.localtime())}.csv'
    result_file = open(result_file_name, 'w')

    time_out = 120 * 10
    num_samples = 1000

    write_file_print(result_file,
                     "filename, Sample_correct_cnt, gen_threshold, runtime(inaccurate), status, IF_frame, K, is_safe, IF_number_safe, IF_number_timeout, IF_number_unsat, Sample_total_pick, Sample_overlap_pick",
                     end='\n')

    for aig_file in traversal_folder(folder_path):
        if '139463p0' in aig_file: continue
        if 'pdtvismiim4' in aig_file: continue
        if 'pdtvisns3p16' in aig_file: continue
        if 'kenflashp06' in aig_file: continue
        if 'boblivear' in aig_file: continue
        if 'pdtvistictactoe12' in aig_file: continue
        if 'pdtvisblackjack3' in aig_file: continue
        if 'nusmvreactorp5' in aig_file: continue
        if '6s410rb043' in aig_file: continue
        if 'pdtvisvsa16a01' in aig_file: continue
        if 'pdtvisvsa16a11' in aig_file: continue
        if '6s421rb083' in aig_file: continue
        if 'pdtvisblackjack1' in aig_file: continue #timeout

        _, filename = os.path.split(aig_file)
        sample_file = sample_path + os.sep + filename[:filename.rindex('.')] + ".sample"

        gen_threshold = 1
        abc_path = "/home/kaiyu/Documents/cab-master/cab"

        while gen_threshold <= 16:
            gen_threshold *= 2
            write_file_print(result_file, filename)
            sample_correct_cnt = len(parse_result_file(sample_file, aig_file, abc_path))
            write_file_print(result_file, sample_correct_cnt)
            write_file_print(result_file, f'Init2_{gen_threshold}')

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


            num_safe, num_timeout, num_unsafe = test_IF_samples_abc(IF_samples, aig_file, time_out, abc_path)
            write_file_print(result_file, num_safe)
            write_file_print(result_file, num_timeout)
            write_file_print(result_file, num_unsafe)

            # print("num_safe: %s, num_timeout: %s, num_unsafe: %s" % (num_safe, num_timeout, num_unsafe))

            IF_total_pick, IF_overlap_pick = parse_raw_output4(raw_output)
            write_file_print(result_file, IF_total_pick)
            write_file_print(result_file, IF_overlap_pick)
            write_file_print(result_file, '', end='\n')

            # parse safe_idx_list
            ic3_safe_index_set = parse_ic3_safe_idx_set(raw_output)
            curr_ic3_safe_index_set = ic3_safe_index_set
            sample_safe_index_set = parse_result_file(sample_file, aig_file, abc_path)
            diff_set = sample_safe_index_set - curr_ic3_safe_index_set

            # print(f'curr_ic3_safe_index_set {len(curr_ic3_safe_index_set)}  {curr_ic3_safe_index_set}')
            # print(f'sample_safe_index_set {len(sample_safe_index_set)} {str(sample_safe_index_set)}')
            # print(f'diff_set {len(diff_set)} {diff_set}')
            #

            print(f'curr_ic3_safe_index_set {len(curr_ic3_safe_index_set)}   sample_safe_index_set {len(sample_safe_index_set)}   diff_set {len(diff_set)}')

            if len(diff_set) == 0:
                print('reach the best AC rate!')
                break

            # init4
            for i in range(5):
                if len(diff_set) == 0:
                    break

                sample_index = random.sample(diff_set, 1)[0]
                # print(f'sample_index {sample_index}')
                new_safe_idx_set, _ = run_Init_2_3_4('Init4', aig_file, result_file, sample_index, sample_file, raw_output, gen_threshold, time_out, i, abc_path)
                # print(f'new_safe_idx_set {len(new_safe_idx_set)} {new_safe_idx_set}')
                before_curr_set_size = len(curr_ic3_safe_index_set)
                curr_ic3_safe_index_set = curr_ic3_safe_index_set.union(new_safe_idx_set)
                after_curr_set_size = len(curr_ic3_safe_index_set)
                assert after_curr_set_size >= before_curr_set_size, 'after_curr_set_size >= before_curr_set_size'

                diff_set = sample_safe_index_set - curr_ic3_safe_index_set
                print(f'curr_ic3_safe_index_set {len(curr_ic3_safe_index_set)}   sample_safe_index_set {len(sample_safe_index_set)}   diff_set {len(diff_set)}')

            if len(diff_set) == 0:
                print('init4 reach the best AC rate!')
                break

            # init3
            for iter in range(2):
                sample_index = -1
                new_safe_idx_set, raw_output = run_Init_2_3_4('Init3', aig_file, result_file, sample_index, sample_file, raw_output,
                                                  gen_threshold, time_out, iter, abc_path)
                print(f'init3_new_safe_idx_set {len(new_safe_idx_set)} {new_safe_idx_set}')
                curr_ic3_safe_index_set = curr_ic3_safe_index_set.union(new_safe_idx_set)
                diff_set = sample_safe_index_set - curr_ic3_safe_index_set
                if len(diff_set) == 0:
                    break

            if len(diff_set) == 0:
                print('init3 reach the best AC rate!')
                break

            #     write_file_print(result_file, filename)
            #
            #     # 3 generate frame file
            #     P, Fi, Symbol_dict, _ = parse_raw_output2(raw_output)
            #     frame_file = aig_file[:aig_file.rindex('.')] + ".frame"
            #     print(frame_file)
            #
            #     write_cubes_of_invariant(Fi, frame_file)
            #
            #     write_file_print(result_file, 'init3_' + str(iter))
            #
            #     # 4: generate raw_output for init3
            #     args = [IC3_init3_path, '-s', '-b', '-p', str(gen_threshold), '-f', frame_file, '-sample', sample_file]
            #     runtime, raw_output = run_IC3(IC3_init3_path, aig_file, gen_threshold, args=args)
            #     write_file_print(result_file, runtime)
            #
            #     if runtime == -1:
            #         write_file_print(result_file, "Timeout Init3", '\n')
            #         break
            #
            #     # 5: Init3 runtime information
            #     IF, K, is_safe_IC3 = parse_raw_output1(raw_output)
            #
            #
            #     # print("IF: %s, K: %s, is_safe_IC3: %s" % (IF, K, is_safe_IC3))
            #
            #     if is_safe_IC3 is None:
            #         write_file_print(result_file, 'core dumped', '\n')
            #         break
            #
            #     # 6: draw samples from the IF using IC3. Test if they are safe using abc.
            #     IF_samples = parse_raw_output3(raw_output)
            #     if IF_samples == None:
            #         write_file_print(result_file, "parse IF samples exception", '\n')
            #         break
            #
            #     if len(IF_samples) == 0:
            #         write_file_print(result_file, "IF is unSAT", '\n')
            #         break
            #     write_file_print(result_file, "Init3 status OK")
            #     write_file_print(result_file, IF)
            #     write_file_print(result_file, K)
            #     write_file_print(result_file, is_safe_IC3)
            #
            #     num_safe, num_timeout, num_unsafe = test_IF_samples_abc(IF_samples, aig_file, time_out)
            #     write_file_print(result_file, num_safe)
            #     write_file_print(result_file, num_timeout)
            #     write_file_print(result_file, num_unsafe)
            #
            #     # print("num_safe: %s, num_timeout: %s, num_unsafe: %s" % (num_safe, num_timeout, num_unsafe))
            #
            #     # 7: randomly draw samples from the whole latch space, and test if they overlap with the IF using IC3.
            #     IF_total_pick, IF_overlap_pick = parse_raw_output4(raw_output)
            #     write_file_print(result_file, IF_total_pick)
            #     write_file_print(result_file, IF_overlap_pick)
            #     write_file_print(result_file, '', '\n')
            #
            #     # print("IF_total_pick: %s, IF_overlap_pick: %s" % (IF_total_pick, IF_overlap_pick))
            # # else:
            # #     write_file_print(result_file, '', '\n')


def parse_ic3_safe_idx_set(raw_output):
    # parse safe_idx_list
    start_index = raw_output.index('safe_idx_list: ') + len('safe_idx_list: ')
    end_index = raw_output.index('IF picks ends.')
    ic3_safe_index_str = str(raw_output[start_index:end_index]).strip()
    if ic3_safe_index_str == '':
        return set()
    return set([int(sample_index) for sample_index in ic3_safe_index_str.split(' ')])


# Cannot handle 2 for now
def run_Init_2_3_4(init_type: str, aig_file_path, result_file, sample_idx, sample_file, prev_raw_output, gen_threshold, time_out, iter_time, abc_path):
    _, aig_file_name = os.path.split(aig_file_path)
    write_file_print(result_file, aig_file_name)
    sample_correct_cnt = len(parse_result_file(sample_file, aig_file_path, abc_path))
    write_file_print(result_file, sample_correct_cnt)

    # 3 generate frame file
    P, Fi, Symbol_dict, latch_list = parse_raw_output2(prev_raw_output)
    frame_file = aig_file_path[:aig_file_path.rindex('.')] + ".frame"

    if init_type == 'Init3':
        write_cubes_of_invariant(Fi, frame_file)
    elif init_type == 'Init4':
        with open(sample_file, 'r') as sf:
            sample = sf.readlines()[sample_idx].strip()

        write_cube_of_samples(sample, latch_list, frame_file)

    write_file_print(result_file, f'{init_type}_' + str(iter_time))

    IC3_init_path = {
        'Init3': '/home/kaiyu/Documents/IC3ref_init3/IC3',
        'Init4': '/home/kaiyu/Documents/IC3ref_init4/IC3',
    }[init_type]

    # 4: generate raw_output for init3
    args = [IC3_init_path, '-s', '-b', '-p', str(gen_threshold), '-f', frame_file, '-sample', sample_file]
    runtime, raw_output = run_IC3(IC3_init_path, aig_file_path, gen_threshold, args=args, timeout_seconds=120)
    write_file_print(result_file, runtime)

    if runtime == -1:
        write_file_print(result_file, f"Timeout {init_type}", '\n')
        return set()

    # 5: Init3 runtime information
    IF, K, is_safe_IC3 = parse_raw_output1(raw_output)

    # print("IF: %s, K: %s, is_safe_IC3: %s" % (IF, K, is_safe_IC3))

    if is_safe_IC3 is None:
        write_file_print(result_file, 'core dumped', '\n')
        return set()

    # 6: draw samples from the IF using IC3. Test if they are safe using abc.
    IF_samples = parse_raw_output3(raw_output)
    if IF_samples == None:
        write_file_print(result_file, "parse IF samples exception", '\n')
        return set()

    if len(IF_samples) == 0:
        write_file_print(result_file, "IF is unSAT", '\n')
        return set()

    write_file_print(result_file, f"{init_type} status OK")
    write_file_print(result_file, IF)
    write_file_print(result_file, K)
    write_file_print(result_file, is_safe_IC3)

    num_safe, num_timeout, num_unsafe = test_IF_samples_abc(IF_samples, aig_file_path, time_out, abc_path)
    write_file_print(result_file, num_safe)
    write_file_print(result_file, num_timeout)
    write_file_print(result_file, num_unsafe)

    # print("num_safe: %s, num_timeout: %s, num_unsafe: %s" % (num_safe, num_timeout, num_unsafe))

    # 7: IF_total_pick: number of samples, IF_overlap_pick: the samples contained in the IF, read from raw_output
    IF_total_pick, IF_overlap_pick = parse_raw_output4(raw_output)
    write_file_print(result_file, IF_total_pick)
    write_file_print(result_file, IF_overlap_pick)
    write_file_print(result_file, '', '\n')

    # print(raw_output)

    return parse_ic3_safe_idx_set(raw_output), raw_output


def parse_result_file(sample_file_path: str, aig_file_path: str, abc_path='/home/kaiyu/Documents/IC3ref_init2/example/youl/abc-master/abc'):
    time_out = 120
    num_samples = 1000

    assert os.path.exists(sample_file_path)
    result_file_path = sample_file_path[:sample_file_path.rindex(".")] + ".result"
    if not os.path.exists(result_file_path):
        print(f"Result file does not exist. Create {result_file_path}")
        get_AC_rate(aig_file=aig_file_path, iter_cnt=num_samples, time_out=time_out, file=sample_file_path, result=result_file_path, abc_path=abc_path)

    with open(result_file_path, 'r') as rf:
        # if len(result_file) < 1000 -> timeout more than 3 times when generating AC rate
        lines = rf.readlines()

        if len(lines) < num_samples:
            # print("result file invalide, timeout > 3")
            return set()

        sample_safe_index_set = set()

        for cnt, line in enumerate(lines):
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


def write_cube_of_samples(sample, latch_list, output_file: str):
    with open(output_file, "w") as of:
        line = ""
        for idx, sign in enumerate(sample):
            line += ' '
            if sign == '0':
                line += '~'
                line += latch_list[idx]
            else:
                line += latch_list[idx]
        line = line.strip()
        line += '\n'
        of.write(line)

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



def main():
    pipeline3()

if __name__ == '__main__':
    main()
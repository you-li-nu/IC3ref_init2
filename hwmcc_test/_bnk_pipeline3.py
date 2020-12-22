from pipeline import traversal_folder, run_IC3, parse_raw_output1, \
    parse_raw_output2, parse_raw_output3, get_AC_rate, parse_raw_output4, test_IF_samples_abc, write_file_print
from rand_init_sampler import read_aig_latch
import time


def pipeline3():
    folder_path = "/home/kaiyu/Documents/IC3ref_init2/example/all_unsafe/"
    IC3_init2_path = '/home/kaiyu/Documents/IC3ref_init2/IC3'
    IC3_init3_path = '/home/kaiyu/Documents/IC3ref_init3/IC3'

    result_file = open('pipeline3_17_unsafe_%s.csv' % (time.strftime("%Y_%b_%d_%H_%M", time.localtime())), 'w')

    for aig_file in traversal_folder(folder_path):

        # if 'beemlmprt8f1.aig' not in aig_file: continue

        # if 'abp4p2ff' not in aig_file: continue
        # if 'mutexp0' not in aig_file: continue

        time_out = 1200
        num_samples = 1000

        print(aig_file)

        # -1: generate random samples
        sample_file_name = aig_file[:aig_file.rindex('.')] + ".sample"
        num_latches = read_aig_latch(aig_file)
        write_samples(file=sample_file_name, seed=0, num_latches=num_latches, num_samples=num_samples)

        # 0
        # randomly draw samples from the whole latch space, and test if they are safe using abc.
        # AC Rate

        AC_timeout_cnt, AC_correct_cnt = get_AC_rate(aig_file, num_samples, time_out, file=sample_file_name)
        # print("AC_timeout_cnt: %s, AC_correct_cnt: %s" % (AC_timeout_cnt, AC_correct_cnt))


        gen_threshold = 1

        while gen_threshold <= 16:
            gen_threshold *= 2

            write_file_print(result_file, aig_file)
            write_file_print(result_file, num_samples)
            write_file_print(result_file, AC_timeout_cnt)
            write_file_print(result_file, AC_correct_cnt)
            write_file_print(result_file, gen_threshold)
            write_file_print(result_file, 'init2')

            # 1: run init2
            args = [IC3_init2_path, '-s', '-b', '-p', str(gen_threshold), '-sample', sample_file_name]
            runtime, raw_output = run_IC3(IC3_init2_path, aig_file, gen_threshold, args=args)
            if runtime == -1:
                write_file_print(result_file, "Timeout Init2", '\n')
                continue

            # 2 IF pick for init 2
            IF, K, is_safe_IC3 = parse_raw_output1(raw_output)
            write_file_print(result_file, IF)
            write_file_print(result_file, K)
            write_file_print(result_file, is_safe_IC3)
            # print("IF: %s, K: %s, is_safe_IC3: %s" % (IF, K, is_safe_IC3))

            if is_safe_IC3 is None:
                write_file_print(result_file, 'core dumped', '\n')
                continue

            IF_samples = parse_raw_output3(raw_output)
            if IF_samples == None:
                write_file_print(result_file, "parse IF samples exception", '\n')
                continue

            if len(IF_samples) == 0:
                write_file_print(result_file, "IF is unSAT", '\n')
                continue

            num_safe, num_timeout, num_unsafe = test_IF_samples_abc(IF_samples, aig_file, time_out)
            write_file_print(result_file, num_safe)
            write_file_print(result_file, num_timeout)
            write_file_print(result_file, num_unsafe)

            # print("num_safe: %s, num_timeout: %s, num_unsafe: %s" % (num_safe, num_timeout, num_unsafe))

            IF_total_pick, IF_overlap_pick = parse_raw_output4(raw_output)
            write_file_print(result_file, IF_total_pick)
            write_file_print(result_file, IF_overlap_pick)

            # print("IF_total_pick: %s, IF_overlap_pick: %s" % (IF_total_pick, IF_overlap_pick))

            for iter in range(2):

                # 3 generate frame file
                P, Fi, Symbol_dict = parse_raw_output2(raw_output)
                frame_file = aig_file[:aig_file.rindex('.')] + ".frame"
                write_cubes_of_invariant(Fi, frame_file)

                write_file_print(result_file, 'init3_' + str(iter))

                # 4: generate raw_output for init3
                args = [IC3_init3_path, '-s', '-b', '-p', str(gen_threshold), '-f', frame_file, '-sample', sample_file_name]
                runtime, raw_output = run_IC3(IC3_init3_path, aig_file, gen_threshold, args=args)
                if runtime == -1:
                    write_file_print(result_file, "Timeout Init3", '\n')
                    break

                # 5: Init3 runtime information
                IF, K, is_safe_IC3 = parse_raw_output1(raw_output)
                write_file_print(result_file, IF)
                write_file_print(result_file, K)
                write_file_print(result_file, is_safe_IC3)

                # print("IF: %s, K: %s, is_safe_IC3: %s" % (IF, K, is_safe_IC3))

                if is_safe_IC3 is None:
                    write_file_print(result_file, 'core dumped', '\n')
                    break

                # 6: draw samples from the IF using IC3. Test if they are safe using abc.
                IF_samples = parse_raw_output3(raw_output)
                if IF_samples == None:
                    write_file_print(result_file, "parse IF samples exception", '\n')
                    break

                if len(IF_samples) == 0:
                    write_file_print(result_file, "IF is unSAT", '\n')
                    break

                num_safe, num_timeout, num_unsafe = test_IF_samples_abc(IF_samples, aig_file, time_out)
                write_file_print(result_file, num_safe)
                write_file_print(result_file, num_timeout)
                write_file_print(result_file, num_unsafe)

                # print("num_safe: %s, num_timeout: %s, num_unsafe: %s" % (num_safe, num_timeout, num_unsafe))

                # 7: randomly draw samples from the whole latch space, and test if they overlap with the IF using IC3.
                IF_total_pick, IF_overlap_pick = parse_raw_output4(raw_output)
                write_file_print(result_file, IF_total_pick)
                write_file_print(result_file, IF_overlap_pick)

                # print("IF_total_pick: %s, IF_overlap_pick: %s" % (IF_total_pick, IF_overlap_pick))
            else:
                write_file_print(result_file, '', '\n')


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



def main():
    pipeline3()

if __name__ == '__main__':
    main()
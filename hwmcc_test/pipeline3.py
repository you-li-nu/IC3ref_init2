from pipeline import traversal_folder, run_IC3, parse_raw_output1, parse_raw_output2, parse_raw_output3


def pipeline3():
    folder_path = "/home/kaiyu/Documents/IC3ref_init2/example/hwmcc17-single-benchmarks/unsafe/"
    IC3_init2_path = '/home/kaiyu/Documents/IC3ref_init2/IC3'
    IC3_init3_path = '/home/kaiyu/Documents/IC3ref_init3/IC3'

    # result_file = open('result.csv', 'w')

    for aig_file in traversal_folder(folder_path):

        if 'beemlmprt8f1.aig' not in aig_file: continue
        gen_threshold = 5.6526


        # generate .frame file
        runtime, raw_output = run_IC3(IC3_init2_path, aig_file, gen_threshold)
        if runtime == -1:
            print("Timeout")
            continue

        P, Fi, Symbol_dict = parse_raw_output2(raw_output)
        frame_file = aig_file[:aig_file.rindex('.')] + ".frame"
        inv_write_cube(Fi, frame_file)

        # generate raw_output for init3
        args = [IC3_init3_path, '-s', '-b', '-p', str(gen_threshold), '-f', frame_file]
        runtime, raw_output = run_IC3(IC3_init3_path, aig_file, gen_threshold, args=args)
        if runtime == -1:
            print("Timeout")
            continue

        # 2
        IF, K, is_safe_IC3 = parse_raw_output1(raw_output)
        # IF: {-1, N^+}
        # K: {-1, N^+}
        # is_safe_IC3: {None (core dumped), True, False}
        print(IF)
        print(K)
        print(is_safe_IC3)

        if is_safe_IC3 is None:
            print('core dumped')
            continue

        P, Fi, Symbol_dict = parse_raw_output2(raw_output)
        # print(P)
        # print(Fi)
        # print(Symbol_dict)

        IF_samples = parse_raw_output3(raw_output)
        print(IF_samples)







def inv_write_cube(Fi, output_file):
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
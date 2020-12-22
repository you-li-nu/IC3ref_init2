

def combine_sample_result_and_ac_rate():
    folder_path = '/home/kaiyu/Documents/hwmcc_benchmarks/classified_benchmarks/'
    sample_result_path = folder_path + 'single_safe_samples.csv'
    ac_rate_path = folder_path + 'single_safe_ac_rate_2020_Dec_16_11_11.csv'
    output_file_path = folder_path + 'single_safe_sample_ac_rate_2020_Dec_16_11_11.csv'

    with open(sample_result_path, 'r') as sf, open(ac_rate_path, 'r') as af, open(output_file_path, 'w') as of:
        sf_header = sf.readline().strip().split(',')
        af_header = af.readline().strip().split(',')
        af_dict = {}
        for line in af:
            cols = line.strip().split(',')
            af_dict[cols[0]] = cols[1:]

        of.write(','.join(sf_header + af_header) + '\n')
        for line in sf:
            of.write(line.strip())
            if not line.strip().endswith(','):
                of.write(',')
            for k, v in af_dict.items():
                if k in line:
                    of.write(f'{k},{",".join(v)}\n')
                    break
            else:
                of.write('\n')


if __name__ == '__main__':
    combine_sample_result_and_ac_rate()
from hwmcc import run_foreground, write_file_print
from pipeline import traversal_folder
import subprocess


def run_iimc(aig_file, tactic='fsis', timeout_seconds=120, args=[], iimc_path=''):
    if iimc_path == '':
        iimc_path = '/home/kaiyu/Documents/iimc_ref/iimc'

    if args == []:
        args = [iimc_path, '-v 4', '-t', tactic, aig_file]

    from datetime import datetime
    start_time = datetime.now()

    import time
    time.sleep(0.01)

    proc = subprocess.Popen(" ".join(args), stdin=None, stdout=subprocess.PIPE, shell=True)

    try:
        proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as err:  # send SIGINT; otherwise kill and report this part
        from signal import SIGINT
        proc.send_signal(SIGINT)
        proc.kill()
        return False, None

    output = proc.stdout.readlines()
    proc.kill()
    return True, "".join(map(lambda x: x.decode(), output))


def parse_iimc_output(output):
    if output.endswith('0\n'):
        return True
    elif output.endswith('1\n'):
        return False
    return None


def main():
    raw_path = "/home/kaiyu/Documents/hwmcc_benchmarks/single/"
    timeout_path = "/home/kaiyu/Documents/hwmcc_benchmarks/single_timeout/"
    unsafe_path = "/home/kaiyu/Documents/hwmcc_benchmarks/single_unsafe/"
    safe_path = "/home/kaiyu/Documents/hwmcc_benchmarks/single_safe/"

    # IC3_path = '/home/kaiyu/Documents/IC3ref_init2/IC3'
    result_file = open('iimc.csv', 'w')
    timeout = 30

    result_cnt = {'timeout': 0, 'unsafe': 0, 'safe': 0}
    for i, aig_file in enumerate(traversal_folder(safe_path)):
        write_file_print(result_file, aig_file)
        is_not_timeout, output = run_iimc(aig_file, timeout_seconds=timeout)

        if is_not_timeout is False:  # timeout
            continue

        print(output)
        is_safe = parse_iimc_output(output)
        print(is_safe)




if __name__ == '__main__':
    main()
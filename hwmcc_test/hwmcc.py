#!/usr/bin/python3
import sys
import os
import subprocess



def main():

    file_path = '/home/li/Documents/IC3ref/example/hwmcc17-single-benchmarks/'
    file_name = 'nusmvguidancep1.aig'
    IC3_path = '/home/li/Documents/IC3ref/IC3'

    result = open("data/result17.txt", "w")

    for subdir, dirs, files in os.walk(file_path):
        for file in files:
            filepath=subdir+os.sep+file
            if not filepath.endswith(".aig") and not filepath.endswith(".aag"):
                continue

            args = [IC3_path]
            print(filepath)
            output = run_foreground(args, f_in=filepath, timeout_seconds=60)
            ans = filepath + ', ' + str(output).strip()
            result.write(filepath + ', ' + str(output).strip() + '\n')
            print(ans)
    result.close()


# run a external program in foreground (e.g. the caller waits until the program exits).
# return:
#   (nullable int) exit_code ("None" when timeout).
#   (nullable str) stdout_text, stderr_text (only when read_output=True)
def run_foreground(args, f_in=None, f_out="./temp_stdout.txt", f_err="./temp_stderr.txt",
  timeout_seconds=3600, read_output=True, killable=False):
    from signal import SIGINT
    stdin, stdout, stderr, exit_code = None, None, None, None
    ## start the program:

    stdin = open(f_in, "r") if f_in else None
    stdout = open(f_out, "w") if f_out else None
    stderr = open(f_err, "w") if f_err else None
    proc = subprocess.Popen(args, stdin=stdin, stdout=stdout, stderr=stderr)

    ## wait for the program to finish:
    is_timeout = False
    try:
        proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as err: # send SIGINT; otherwise kill and report this part
        is_timeout = True
        # print(err)
        proc.send_signal(SIGINT)
        proc.kill()  # brute-force kill
        return -1
    else:
        exit_code = proc.returncode

    ## clean things up:
    for fp in stdin, stdout, stderr:
        if fp: fp.close()
    if read_output:
        stdout_text = _read_optional(f_out)
        stderr_text = _read_optional(f_err)
        if exit_code == 1:
            return stdout_text
        else:
            return 'exit_code: ' + str(exit_code)
    else:
        return -2


# return filename's content, or None if it does not exist.
# nullable(str) -> nullable(str)
def _read_optional(filename):
    if filename is None:
        return None
    try:
        with open(filename, "r") as f:
            return f.read()
    except IOError:
        return None
    except UnicodeDecodeError: # UnicodeDecodeError: 'utf-8' codec can't decode byte ...
        with open(filename, "rb") as f:
            return str(f.read())


def write_file_print(f, text, end=','):
    text = str(text)
    f.write(text + end)
    print(text, end=end)


if __name__ == '__main__':
    main()

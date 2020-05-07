from pycryptosat import *
import sys
import os
import shutil
import subprocess
import re

from hwmcc import _read_optional, run_foreground, write_file_print



def main():

    file_path = "/home/li/Documents/IC3ref_init/example/hwmcc17-single-benchmarks/"
    # IC3_path = '/home/li/Documents/IC3ref_init2/IC3'

    safe_dir = file_path + "/safe/"
    unsafe_dir = file_path + "/unsafe/"
    timeout_dir = file_path + "/timeout/"

    if os.path.exists(safe_dir):
        shutil.rmtree(safe_dir)
    if os.path.exists(unsafe_dir):
        shutil.rmtree(unsafe_dir)
    if os.path.exists(timeout_dir):
        shutil.rmtree(timeout_dir)

    os.mkdir(safe_dir)
    os.mkdir(unsafe_dir)
    os.mkdir(timeout_dir)

    result_file = open("data/IC3_IF_17.txt", 'r')
    lines = result_file.readlines()

    for line in lines:
        print(line)
        if line.strip().endswith("0"):
            file_name = line[line.rindex("/") + 1 : line.index(',')]
            shutil.copyfile(line[:line.index(',')], file_path + "/safe/" + file_name)
        elif line.strip().endswith("1"):
            file_name = line[line.rindex("/") + 1 : line.index(',')]
            shutil.copyfile(line[:line.index(',')], file_path + "/unsafe/" + file_name)
        elif line.strip().endswith("timeout"):
            file_name = line[line.rindex("/") + 1 : line.index(',')]
            shutil.copyfile(line[:line.index(',')], file_path + "/timeout/" + file_name)
        elif line == "\n":
            continue
        else:
            print("unknown problem! " + line)










if __name__ == '__main__':
    main()
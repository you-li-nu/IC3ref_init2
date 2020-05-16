import csv
import matplotlib.pyplot as plt


def datetime2sec(time: str):
    ans = 0
    for t in time.split(":"):
        ans *= 60
        ans += float(t)
    return ans



lines = []
with open('first_run_pipe.csv') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for line in reader:
        lines.append(line)
        # print(line)


lines = lines[1:]
files = {}  # file: data, data = {column_name: list}

column_names = ["Threshold", "AC_Rate", "IC3_Runtime", "IF", "K", "Total_Samples", "AC_Pick"]
names_to_index = {"Threshold": 3, "AC_Rate": 2, "IC3_Runtime": 4, "IF": 5, "K": 6, "Total_Samples": 8, "AC_Pick": 9}


for line in lines:
    filename = line[0].split('/')[-1]
    if filename not in files.keys():
        files[filename] = {name: [] for name in column_names}
    for column_name in column_names:
        files[filename][column_name].append(line[names_to_index[column_name]])

print(files)

fig, ax = plt.subplots(nrows=4, ncols=4)
for i, filename in enumerate(files.keys()):
    size = len(files[filename]["Threshold"])
    runtime = []
    for time in files[filename]["IC3_Runtime"]:
        if time == 'timeout':
            runtime.append(40)
        else:
            runtime.append(datetime2sec(time))

    ratio = []
    for j in range(size):
        if files[filename]["AC_Pick"][j] == '':
            ratio.append(0)
        elif files[filename]["AC_Rate"][j] == '0':
            ratio.append(0)
        else:
            ratio.append(int(files[filename]["AC_Pick"][j]) / int(files[filename]["AC_Rate"][j]))


    ax[i // 4, i % 4].plot(list(range(size)), runtime, label='IC3_Runtime')
    ax[i // 4, i % 4].plot(list(range(size)), ratio, label='IC3_Ratio')
    ax[i // 4, i % 4].legend()


# plt.xticks(list(range(size)), files[filename]["Threshold"])
plt.show()


    # break









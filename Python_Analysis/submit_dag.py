from argparse import ArgumentParser
import subprocess
from subprocess import Popen
import os
import json


def make_parser():
    parser = ArgumentParser(description="Submit Dag Jobs automatically.")
    parser.add_argument('-i', '--input_dir', type=str,
                        help="/afs/ base dir to submit from", default=None)
    parser.add_argument('-o', "--output_dir", type=str,
                        help="/eos/ base dir to store data", default=None)
    parser.add_argument('-e', "--executable", type=str, default=None,
                        help="full path to executable to run for each dag entry.")
    parser.add_argument('-j', "--json", type=str,
                        help="json file with datasets and xs..", default=None)
    parser.add_argument('-p', "--proxy", type=str,
                        help="full path to voms cms user proxy", default=None)
    parser.add_argument('-m', '--mc', action='store_true',
                        help="If set, will write files for MC.")
    return parser


def return_subfile(input_dir, base_dir, executable, mc):
    if not executable.startswith("/"):
        executable = '/afs/cern.ch/user/j/jowulff/Condor/TTbar/PythonAnalysis/'+executable
    if mc:
        arguments='Arguments = -i $(INFILE) -o $(OUTFILE) -x $(XS) -l $(LUMI) -p $(PROXY)\n'
    else:
        arguments='Arguments = -i $(INFILE) -o $(OUTFILE) -f $(FIRST_DATA) -p $(PROXY)\n'
    file_str = f"basedir={input_dir}\n\
\n\
executable={executable}\n\
should_transfer_files = YES\n\
when_to_transfer_output = ON_EXIT\n\
\n\
output                = {base_dir}/out/$(ClusterId).$(ProcId).out\n\
error                 = {base_dir}/err/$(ClusterId).$(ProcId).err\n\
log                   = {base_dir}/log/$(ClusterId).$(ProcId).log\n\
\n\
+JobFlavour = \"longlunch\"\n"+arguments+"\nqueue"
    return file_str


def main():
    parser = make_parser()
    args = parser.parse_args()
    input_dir = args.input_dir
    output_dir = args.output_dir
    executable = args.executable
    mc = args.mc
    proxy = args.proxy
    if not proxy.startswith("/"):
        proxy = input_dir+'/'+proxy
    for fd in [input_dir, output_dir, proxy, executable]:
        if not os.path.exists(fd):
            raise ValueError(f"{fd} does not exist.\
    Check your input or create it first.")
    data_json = open(args.json)
    data = json.load(data_json)
    jobscript = '/eos/user/j/jowulff/TTbar/PythonAnalysis/write_dag.sh'
    with open("./commands.txt", 'a') as commandfile:
        for sample in data:
            basedir = input_dir+f"/{sample}"
            submit_file_str = return_subfile(input_dir=input_dir,
                                            base_dir=basedir,
                                            executable=executable, 
                                            mc=mc)
            for io_dir in [basedir, f"{output_dir}/{sample}"]:
                if not os.path.exists(io_dir):
                    print(f"{io_dir} does not exist. Creating it now")
                    os.mkdir(io_dir)
            dataset = data[sample]['dataset']
            if mc==True:
                xsec = data[sample]['xs']
                lumi = 59.82
                cmd = f"{jobscript} -s {basedir}/{sample}.submit \
-j {basedir}/{sample}.dag -d {dataset} -o {output_dir}/{sample} \
-x {xsec} -l {lumi} -p {proxy}"
            else:
                first_data = data[sample]['first_data']
                if first_data:
                    cmd = f"{jobscript} -s {basedir}/{sample}.submit \
-j {basedir}/{sample}.dag -d {dataset} -o {output_dir}/{sample} \
-f true -p {proxy}"
                else:
                    cmd = f"{jobscript} -s {basedir}/{sample}.submit \
-j {basedir}/{sample}.dag -d {dataset} -o {output_dir}/{sample} \
-p {proxy}"
            print(cmd, file=commandfile)
            write_dagfile = Popen(cmd.split(), stdout=subprocess.PIPE)
            wd_out, wd_err = write_dagfile.communicate()
            # 'x' file opening mode means exclusive creation. Fails if file exists
            with open(f"{basedir}/{sample}.submit", 'x') as file:
                print(submit_file_str, file=file)

            for directory in ['err', 'log', 'out']:
                if not os.path.exists(f"{basedir}/{directory}"):
                    os.mkdir(f"{basedir}/{directory}")


if __name__ == "__main__":
    main()

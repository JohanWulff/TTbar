from argparse import ArgumentParser
from subprocess import Popen, PIPE
import sys
import os
import json


def make_parser():
    parser = ArgumentParser(description="Submit Dag Jobs automatically.")
    parser.add_argument('-i', '--input_dir', type=str,
                        help="/afs/ base dir to submit from", default=None)
    parser.add_argument('-o', "--output_dir", type=str,
                        help="/eos/ base dir to store data", default=None)
    parser.add_argument('-e', "--executable", type=str, default=None,
                        help="full path to executable to run for \
each dag entry.")
    parser.add_argument('-j', "--json", type=str,
                        help="json file with datasets and xs..", default=None)
    parser.add_argument('-p', "--proxy", type=str,
                        help="full path to voms cms user proxy", default=None)
    parser.add_argument('-m', '--mc', action='store_true',
                        help="If set, will write files for MC.")
    return parser


def return_subfile(input_dir, base_dir, executable, mc, sum_w=False):
    if not executable.startswith("/"):
        executable = '/afs/cern.ch/user/j/jowulff/Condor/\
TTbar/PythonAnalysis/'+executable
    if mc:
        if sum_w is False:
            arguments = 'Arguments = -i $(INFILE) -o $(OUTFILE) \
-x $(XS) -l $(LUMI) -p $(PROXY)\n'
        else:
            arguments = 'Arguments = -i $(INFILE) -o $(OUTFILE) \
-x $(XS) -l $(LUMI) -w $(SUM_W) -p $(PROXY)\n'
    else:
        arguments = 'Arguments = -i $(INFILE) -o $(OUTFILE) \
-f $(FIRST_DATA) -p $(PROXY)\n'
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


def run_dasgoclient(dataset: str):
    """
    Runs dasgoclient and returns a list of files for a given dataset
    """
    cmd = f'dasgoclient -query="file dataset={dataset}"'
    process = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, encoding='utf-8')
    out, err = process.communicate()
    if err:
        print(err)
        sys.exit(1)
    else:
        return out.split()


def write_dag(dagfile, subfile: str,
              infile: str, outfile: str,
              proxy: str,
              first_data: bool,
              mc: bool,
              xs: float = None,
              lumi: int = None,
              sum_w: float = None):
    jobid = infile.split('/')[-1]
    infile = f"root://cms-xrd-global.cern.ch//{infile}"
    print(f"JOB {jobid} {subfile}", file=dagfile)
    if mc:
        if sum_w != None:
            print(f"VARS {jobid} INFILE=\"{infile}\" \
OUTFILE=\"{outfile}\" XS=\"{xs}\" LUMI=\"{lumi}\" \
SUM_W=\"{sum_w}\" PROXY=\"{proxy}\"", file=dagfile)
        else:
            print(f"VARS {jobid} INFILE=\"{infile}\" \
OUTFILE=\"{outfile}\" XS=\"{xs}\" LUMI=\"{lumi}\" \
PROXY=\"{proxy}\"", file=dagfile)
    else:
        print(f"VARS {jobid} INFILE=\"{infile}\" \
OUTFILE=\"{outfile}\" -f {first_data} PROXY=\"{proxy}\"", file=dagfile)


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
        if mc is True:
            xsec = data[sample]['xs']
            lumi = 59.82
            sum_w = data[sample]['Sum_w']
            datafiles = run_dasgoclient(dataset=dataset)
            with open(f"{basedir}/{sample}.dag") as dagfile:
                for file in datafiles:
                    write_dag(dagfile=dagfile,
                              subfile=f"{basedir}/{sample}.submit",
                              infile=file, outfile=f"{output_dir}/{sample}",
                              proxy=proxy, mc=mc, xs=xsec, lumi=lumi)
        else:
            first_data = data[sample]['first_data']
            with open(f"{basedir}/{sample}.dag") as dagfile:
                for file in datafiles:
                    write_dag(dagfile=dagfile,
                              subfile=f"{basedir}/{sample}.submit",
                              infile=file,
                              outfile=f"{output_dir}/{sample}",
                              first_data=first_data,
                              proxy=proxy,
                              mc=mc)
        with open(f"{basedir}/{sample}.submit", 'x') as file:
            print(submit_file_str, file=file)

        for directory in ['err', 'log', 'out']:
            if not os.path.exists(f"{basedir}/{directory}"):
                os.mkdir(f"{basedir}/{directory}")


if __name__ == "__main__":
    main()

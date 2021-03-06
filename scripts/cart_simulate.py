#!/usr/bin/env python


import os
import subprocess
import sys
import shlex

from asreviewcontrib.hyperopt.job_utils import get_data_names
from asreviewcontrib.simulation.batch_entry import _batch_parser


BATCH_TEMPLATE = """\
#!/bin/bash

#SBATCH -t {time}
#SBATCH --tasks-per-node {tasks_per_node}
#SBATCH -p {node_type}
#SBATCH -N {num_nodes}
#SBATCH -J hyper_{job_name}
#SBATCH --output={batch_dir}/cart.out
#SBATCH --error={batch_dir}/cart.err

module load eb

cd {cur_dir}
source ~/py-env/asreview/bin/activate

srun asreview batch {args}

date

"""


def main(cli_args):
    job_name = input("Please enter job name for simulation:  ")

    parser = _batch_parser()
    parser.add_argument("-t", "--time",
                        type=str, default="120:00:00",
                        help="Maximum clock wall time for the optimization"
                        " to run.")
    args = vars(parser.parse_args(cli_args[1:]))
    cur_dir = os.getcwd()
    time = args.pop("time")

    split_time = time.split(":")
    if len(split_time) == 1:
        minutes = int(time)
    elif len(split_time) == 2:
        minutes = int(split_time[0]) + int(split_time[1])/60
    elif len(split_time) == 3:
        double_split = split_time[0].split("-")
        if len(double_split) == 2:
            hours = int(double_split[0])*24
            hours += int(double_split[1])
        else:
            hours = int(split_time[0])
        minutes = 60*hours + int(split_time[1]) + int(split_time[2])/60

    if minutes > 60:
        node_type = "normal"
    else:
        node_type = "short"

    time_pos = None
    try:
        time_pos = cli_args.index('-t')
    except ValueError:
        try:
            time_pos = cli_args.index('--time')
        except ValueError:
            pass
    if time_pos is not None:
        del cli_args[time_pos:time_pos+2]

    batch_dir = os.path.join(cur_dir, "hpc_batch_files", job_name)
    batch_file = os.path.join(batch_dir, "batch.sh")

    total_jobs = args["n_run"]
    if os.path.isfile(batch_file):
        print(f"Error: batch file exists. Delete {batch_file} to continue.")
        sys.exit(192)

    if total_jobs + 1 > 24:
        n_tasks = 24
    else:
        n_tasks = total_jobs + 1

    if 'model' in args and args['model'].startswith('lstm'):
        tasks_per_node = 6
        num_nodes = min(5, max(1, n_tasks//tasks_per_node))
    else:
        tasks_per_node = n_tasks
        num_nodes = 1

    batch_str = BATCH_TEMPLATE.format(
        job_name=job_name, tasks_per_node=tasks_per_node,
        num_nodes=num_nodes, args=" ".join(cli_args), cur_dir=cur_dir,
        time=time, batch_dir=batch_dir, node_type=node_type)

    os.makedirs(batch_dir, exist_ok=True)
    with open(batch_file, "w") as fp:
        fp.write(batch_str)

    subprocess.run(shlex.split(f"sbatch {batch_file}"))


if __name__ == "__main__":
    main(sys.argv[1:])

import json
import subprocess
from datetime import datetime
from pathlib import Path

from cascoda.whitefield import run_simulation


def run_config(s, nP, c, ping, path):
    # function to run the sim
    outfile = "wf_ot_n3_t1_s" + str(s) + "_x" + str(c) + "_p" + str(ping) + ".cfg"
    outfile_path = path + outfile

    command = (
        "./config-editor.sh -n 3 -t 1 -s "
        + str(s)
        + ' -x "'
        + str(nP)
        + '" -p "'
        + str(ping)
        + '" -i ../config/wf_ot_v1_8.cfg -o '
        + outfile_path
    )

    subprocess.run(command, shell=True)

    return outfile, outfile_path


def detect_hnp(log_path, outlog_file, sens, nPos, simulation_outputs):
    # function that returns False is no hidden node and True is hidden node detected
    with open(log_path) as airline_log:
        if "snr <= snr_min, dropped" in airline_log.read():
            with open(outlog_file, "a") as f:
                f.writelines(
                    [
                        "\nHidden Node Problem detected at:",
                        "\nrxSensitivity=",
                        str(sens),
                        "\nnodePosition=",
                        nPos,
                        "\n",
                        "\nThe simulations output directories:",
                        json.dumps(simulation_outputs, sort_keys=False, indent=4),
                        "\n",
                    ]
                )
            return True
        else:
            return False


def nodePos_change(nP, c):
    # function to change the node positions
    nPos_changed = ""
    for i in nP.split():
        pos = i.strip("[]").split(",")
        pos[1] = str(int(int(pos[1]) * 0.5 * (c + 1)))
        nPos_changed += "["
        for i in pos:
            nPos_changed += i + ","
        nPos_changed += "]"
    nPos_changed = nPos_changed.replace(",]", "]").replace("][", "] [")
    return nPos_changed


def workflow():
    for sens in range(-99, -106, -1):
        nodePos = "[0,0,0] [0,10,0] [0,20,0]"
        count = 0
        # ping is still hardcoded, but is now changeable (like sens and newNodePos)
        ping = 83
        hidden_node = False
        current_date_formatted = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        # create logs folder if not exist
        Path("../logs").mkdir(exist_ok=True, parents=True)
        log_file = "../logs/sim_runs_" + current_date_formatted + ".log"
        with open(log_file, "w") as f:
            f.write(
                "Results from simulation runs started at: " + current_date_formatted
            )
        # print("\n")

        while hidden_node is False:
            newNodePos = nodePos_change(nodePos, count)
            count = count + 1

            configfile, configfile_path = run_config(
                sens, newNodePos, count, ping, "../config/"
            )

            simulation_output_logs = run_simulation(configfile_path)
            airline_log_path = str(simulation_output_logs["log"]) + "/airline.log"
            # print(f"************* airline log path here {airline_log_path}")

            # For logging purposes. Convert Dict to List of absolute paths
            printable_sim_output_paths = [
                str(path.resolve()) for (folder, path) in simulation_output_logs.items()
            ]

            hidden_node = detect_hnp(
                airline_log_path,
                log_file,
                sens,
                newNodePos,
                printable_sim_output_paths,
            )

            if count == 50:
                with open(log_file, "a") as f:
                    f.write("\nHidden Node problem not detected after 50 iterations.")
                break


if __name__ == "__main__":
    workflow()

import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

interrupt = False


def signal_handler(signal, frame):
    global interrupt
    interrupt = True
    print("You pressed Ctrl+C!")
    # sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

WHITEFIELD_PATH = "../../whitefield/"
CONFIG_PATH_OT = "../config/wf_ot_v1_8.cfg"
SIMULATION_OUTPUTS = "../simulation_outputs"
CASCODA_PATH = "../ot-wf-results-gen/cascoda/"


def create_backup_dirs(config_file, folders=["log", "pcap"]):
    output_dirs = {}
    for folder in folders:
        current_date_formatted = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        timestampedFolder = folder + "_" + current_date_formatted
        output_backup_dir = Path(
            SIMULATION_OUTPUTS + "/" + Path(config_file).stem + "/" + timestampedFolder
        )
        print("output dir =", output_backup_dir)
        # output_backup_dir.mkdir(exist_ok=True, parents=True)
        output_dirs[folder] = output_backup_dir

    return output_dirs


# to move folder one directory up
# https://stackoverflow.com/a/50368037
def backup_log_pcap_files(config_file, folders=["log", "pcap"]):
    # ensure directories exist (create if not exist) before attempting to move
    # log folders
    print(f"Whitefield processed the current config: {config_file}")
    print("Backing up pcap and log folders.")
    output_dirs = create_backup_dirs(config_file, folders)
    for folder in folders:
        original_path = Path(WHITEFIELD_PATH + folder)
        # print(f"moving folder {folder}s from", original_path)
        # print("to output_dir", output_dirs[folder])
        shutil.move(str(original_path), str(output_dirs[folder]))
    return output_dirs


def clear_screen():
    subprocess.call(["clear"])


def progress_bar(n, max_dots=6):
    # progress bar resets dots to 0 when n == max dots
    sys.stdout.write(
        "\rProcessing %s%s"
        % ((n % max_dots) * ".", (max_dots - 1 - (n % max_dots)) * " ")
    )
    sys.stdout.write("\rProcessing %s" % ((n % max_dots) * "."))
    sys.stdout.flush()


# start whitefield
def start(config_file):
    output = subprocess.run(
        ["./invoke_whitefield.sh", config_file],
        cwd=WHITEFIELD_PATH,
        capture_output=True,
    )
    print(output.stdout.decode("utf-8").rstrip(), "\n")
    if "Started OK" not in output.stdout.decode("utf-8").rstrip():
        print("ERROR config file not found (look for typos)")
        # sys.exit()
    sys.stdout.flush()


# stop whitefield
def stop():
    output = subprocess.run(
        ["./scripts/wfshell", "stop_whitefield"],
        cwd=WHITEFIELD_PATH,
        capture_output=True,
    )
    print(output.stdout.decode("utf-8").rstrip(), "\n")
    sys.stdout.flush()


def whitefield_status():
    sys.stdout.flush()
    status_output = []
    output = subprocess.Popen(
        ["./whitefield_status.sh"],
        cwd=WHITEFIELD_PATH + "/scripts",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    for line in iter(output.stdout.readline, b""):
        # sys.stdout.flush()
        # decode bytes for cleaner output
        # print(line.decode("utf-8").rstrip())
        status_output.append(line.decode("utf-8").rstrip())
        # sys.stdout.flush()
    return status_output


def monitor(method_to_monitor, timer=2):
    """
    Prints output of method_to_monitor() to a blank screen for timer seconds.
    If Ctrl+C is pressed, the signal_handler is invoked and terminates this loop
    """
    # clear_screen()
    output = []
    n = 0
    while not ("Whitefield stopped" in output):
        # global interrupt set to true in signal_handler() on 'Ctrl+C'
        if interrupt:
            break
        else:
            progress_bar(n)
            # print output of method_to_monitor() for timer seconds
            output = method_to_monitor()
            if "Whitefield stopped" in output:
                break
            time.sleep(timer)
            # clear_screen()
            n += 1
            continue
    sys.stdout.flush()
    print("\n")


def run_simulation(config_file):
    """
    Runs simulation, and returns the directories of the output files (logs and pcaps)
    whitefield has a constraint where it can only be invoked under WHITEFIELD_PATH.
    CASCODA_PATH allows the start() method to find the configs
    """
    print("\n")
    print("---------------------" * 3)
    print("invoking whitefield with " + CASCODA_PATH + config_file)
    start(CASCODA_PATH + config_file)
    monitor(whitefield_status, timer=2)
    stop()
    return backup_log_pcap_files(config_file)


if __name__ == "__main__":
    run_simulation(CONFIG_PATH_OT)

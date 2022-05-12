import csv
import os
import re
import subprocess
import sys
from typing import Any, Tuple

import numpy as np


# A list of filtered packets extracted from the pcap file
# if used on central node, these are the replies packets sent to all end nodes
# if used on end nodes, these are the total packets sent
def tshark_get_filtered_packets(pcap_directory: str, pcap_file: str) -> list[str]:
    output = subprocess.run(
        ["tshark", "-r", pcap_directory + pcap_file, "-Y", "icmpv6"],
        capture_output=True,
    )
    string_output = output.stdout.decode("utf-8").rstrip()
    split_string_output = string_output.splitlines()

    return split_string_output


# extracts the packet sequence number from a single packet
def get_seq_value(packet_string: str) -> int:
    seq_value_index = packet_string.find("seq=") + 4

    return int(packet_string[seq_value_index:].split(",")[0])


def get_source(packet_string: str) -> str:
    return packet_string.strip().split(" ")[3]


def get_sources_list(tshark_output: list[str]) -> list[str]:
    return [get_source(packet_string) for packet_string in tshark_output]


def get_destination(packet_string: str) -> str:
    return packet_string.strip().split(" ")[5]


def get_destination_list(tshark_output: list[str]) -> list[str]:
    return [get_destination(packet_string) for packet_string in tshark_output]


def filtered_response_sequences(central_node, node_0, node_2):
    """
    Returns lists of responses (sequence numbers) grouped by end node
    """
    # get end nodes address
    node_0_address = get_sources_list(node_0)[0]
    node_2_address = get_sources_list(node_2)[0]

    filtered_sequences_0 = []
    filtered_sequences_2 = []

    destinations = get_destination_list(central_node)
    sequences = get_sequences_list(central_node)
    for i in range(len(destinations)):
        if destinations[i] == node_0_address:
            filtered_sequences_0.append(sequences[i])
        else:
            filtered_sequences_2.append(sequences[i])

    print(node_0_address, node_2_address)

    return filtered_sequences_0, filtered_sequences_2


# extracts a list of sequence numbers from the packets
def get_sequences_list(tshark_output: list[str]) -> list[int]:
    return [get_seq_value(packet_string) for packet_string in tshark_output]


# extracts the time value from a single packet
def get_time(packet_string: str) -> str:
    return packet_string.strip().split(" ")[2]


# extracts a list of times from the packets
def get_times_list(tshark_output: list[str]) -> list[str]:
    return [get_time(packet_string) for packet_string in tshark_output]


def get_files(rootdir: str) -> Tuple[list[str], dict[str, list[str]]]:
    pcap_file_paths = {}
    config_files = []

    for dir in next(os.walk(rootdir))[1]:
        pcap_dirs = [x for x in next(os.walk(rootdir + "/" + dir))[1] if "pcap" in x]
        config_file = dir + ".cfg"
        config_files.append(config_file)
        for pcap_dir in pcap_dirs:
            pcap_files = os.listdir(os.path.join(rootdir, dir, pcap_dir))
            pcap_file_paths_list = []
            for pcap_file in pcap_files:
                pcap_file_paths_list.append(
                    os.path.join(rootdir, dir, pcap_dir, pcap_file)
                )
        pcap_file_paths.update({dir: pcap_file_paths_list})

    return config_files, pcap_file_paths


def max_theoretical_ping(config_file_path: str) -> int:
    with open(config_file_path, "r") as f:
        max_theoretical = 0
        for ln in f:
            if ln.startswith("nodePing"):
                num = ln.split(" ")[3]
                max_theoretical = max_theoretical + int(num)

    return max_theoretical


# used as a key for sorting the pcap directories (based on sensitivity)
def extract_sensitivity(line):
    # everything after "s-" (sensitivity)
    post_sens = line.split("-")[1]
    sens_end_index = post_sens.find("_")
    return int(post_sens[0:sens_end_index])


# return type -> Tuple[list[int], list[int]]:
def retries_per_unique_sequence_number(sequences: list[int]):
    """
    Returns the number of retries for each unique sequence number in the pcap file.
    """
    unique_values, counts = np.unique(sequences, return_counts=True)
    retries = [count - 1 for count in counts]
    unique_values = unique_values.tolist()

    return unique_values, retries


def retries_per_packet(sequences: list[int]) -> list[int]:
    """
    This returns the number of retries sequentially (for the entire pcap)
    by tracking repitions in count_retries.
    Includes retries with value 0 (packet was sent Once, with no re-attempts).
    Can be used to track retries over time
    """

    retries = []
    count_retries = 0
    # these two values are different to ensure they don't get treated as ==
    prev_value = -1
    current_value = 0
    for sequence in sequences:
        current_value = sequence
        if current_value == prev_value and current_value != 0 and prev_value != 0:
            count_retries += 1
            retries.append(count_retries)
        elif current_value != prev_value and current_value != 0 and prev_value != 0:
            # the count has reset. store, and reset to 0
            retries.append(count_retries)
            count_retries = 0

        prev_value = current_value

        # print(f"loop state. {current_value}, {prev_value}, {count_retries}")

    return retries


def get_stats(pcap_directory, config_file_path) -> dict[str, Any]:
    print(f"stats for pcap {pcap_directory} and config {config_file_path}")
    stats = dict[str, Any]()
    packets_list_node0 = tshark_get_filtered_packets(
        pcap_directory, pcap_file="pkt-0-0.pcap"
    )
    packets_list_node1 = tshark_get_filtered_packets(
        pcap_directory, pcap_file="pkt-1-0.pcap"
    )
    packets_list_node2 = tshark_get_filtered_packets(
        pcap_directory, pcap_file="pkt-2-0.pcap"
    )

    sequence_list_0 = get_sequences_list(packets_list_node0)
    sequence_list_2 = get_sequences_list(packets_list_node2)
    # link retries and times together (via sequence?)
    time_list_0 = get_times_list(packets_list_node0)
    time_list_2 = get_times_list(packets_list_node2)

    # the responses from central sent to (and filtered by) end nodes
    filtered_responses_0, filtered_responses_2 = filtered_response_sequences(
        packets_list_node1, packets_list_node0, packets_list_node2
    )

    # total replies sent to node 0 and 2.
    stats["replies_from_central_node"] = len(packets_list_node1)
    # max theoretical replies (if network had no collisions)
    stats["max_theoretical"] = max_theoretical_ping(config_file_path)

    stats["replies_to_0"] = len(filtered_responses_0)
    stats["replies_to_2"] = len(filtered_responses_2)

    stats["packets_sent_0"] = len(packets_list_node0)
    stats["packets_sent_2"] = len(packets_list_node2)
    stats["total_packets_sent"] = stats["packets_sent_0"] + stats["packets_sent_2"]

    # unique packets sent (aka highest sequence number)
    stats["unique_packets_sent_0"] = len(set(sequence_list_0))
    stats["unique_packets_sent_2"] = len(set(sequence_list_2))
    stats["total_unique_packets_sent"] = (
        stats["unique_packets_sent_0"] + stats["unique_packets_sent_2"]
    )

    stats["retries_per_unique_sequence_node_0"] = retries_per_unique_sequence_number(
        sequence_list_0
    )[1]

    stats["retries_per_unique_sequence_node_2"] = retries_per_unique_sequence_number(
        sequence_list_2
    )[1]

    stats["sequence_numbers_0"] = sequence_list_0
    stats["sequence_numbers_2"] = sequence_list_2

    stats["time_0"] = time_list_0
    stats["time_2"] = time_list_2

    # Metrics central node
    # A) total replies / total sent (to central node)
    stats["%_responded"] = (
        stats["replies_from_central_node"] / stats["total_packets_sent"]
    ) * 100

    stats["%_responded"] = round(stats["%_responded"], 2)

    # B) total replies / max theoretical replies
    stats["network_efficiency_%"] = (
        stats["replies_from_central_node"] / stats["max_theoretical"]
    ) * 100

    stats["network_efficiency_%"] = round(stats["network_efficiency_%"], 2)

    # Metrics end nodes
    # C) X requests were sent, Y were unique"
    stats["Node_0_request_stat"] = (
        f'Node 0: {stats["packets_sent_0"]} requests were sent, '
        + f'{stats["unique_packets_sent_0"]} were unique'
    )

    stats["Node_2_request_stat"] = (
        f'Node 2: {stats["packets_sent_2"]} requests were sent, '
        + f'{stats["unique_packets_sent_2"]} were unique'
    )

    config_params = [float(s) for s in re.findall(r"-?\d+\.?\d*", config_file_path)]

    stats["n"] = config_params[0]
    stats["t"] = config_params[1]
    stats["s"] = config_params[2]
    stats["x"] = config_params[3]
    stats["p"] = config_params[4]

    return stats


# parent function for get_stats()
def config_pcap_get_stats(rootdir):
    all_stats = []
    config_files, pcap_file_paths = get_files(rootdir)
    # the first sort, sorts all paths by increasing each parameter in order
    config_files.sort()
    # but instead of -105 to -99 sensitivity we want to decrease sensitivity
    # decrease the sensitivites from the sorted lists (by ignoring the -ve sign)
    config_files.sort(key=extract_sensitivity)
    for path in config_files:
        print("------------------" * 4)
        config_file_path = os.path.join("../config", path)
        print(f"Path: {config_file_path}")
        # config file is key to access pcap files
        config_file_key = os.path.basename(path).split(".")[0]
        # using any pcap path ([0] was chosen) access the full parent directory
        pcap_dir = os.path.dirname(pcap_file_paths[config_file_key][0])
        # adds required trailing slash if not present, no change if present
        pcap_dir = os.path.join(pcap_dir, "")
        print("Pcap directory to extract/build stats from", pcap_dir)
        stats = get_stats(pcap_dir, config_file_path)
        # all stats can also be a dict using config or pcap_dir as key
        all_stats.append(stats)
    return all_stats


def export_stats_to_csv(
    all_stats, filename="../outputs/hidden_node_simulation_export.csv"
):
    fields = all_stats[0].keys()
    with open(filename, "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_stats)


if __name__ == "__main__":
    rootdir = "../simulation_outputs"
    all_stats = config_pcap_get_stats(rootdir)
    if len(sys.argv) == 1:
        export_stats_to_csv(all_stats)
    elif str(sys.argv[1]) == "":
        export_stats_to_csv(all_stats)
    else:
        export_stats_to_csv(all_stats, filename=str(sys.argv[1]))

"""Script for testing the automated labeler"""

import argparse
import json
import os
import ast

import time
import tracemalloc
import requests
import psutil

import pandas as pd
from atproto import Client
from dotenv import load_dotenv

from pylabel import label_post, did_from_handle
from giveaway_labeler.policy_proposal_labeler import AutomatedLabeler

load_dotenv(override=True)
USERNAME = os.getenv("USERNAME")
PW = os.getenv("PW")

def main():
    """
    Main function for the test script
    """
    client = Client()
    labeler_client = None
    client.login(USERNAME, PW)
    did = did_from_handle(USERNAME)

    parser = argparse.ArgumentParser()
    parser.add_argument("labeler_inputs_dir", type=str)
    parser.add_argument("input_urls", type=str)
    parser.add_argument("--emit_labels", action="store_true")
    args = parser.parse_args()

    if args.emit_labels:
        labeler_client = client.with_proxy("atproto_labeler", did)

    labeler = AutomatedLabeler(client, args.labeler_inputs_dir)

    urls = pd.read_csv(args.input_urls, converters={"Labels": ast.literal_eval})
    num_correct, total = 0, urls.shape[0]
    label_counter = {}
    for _index, row in urls.iterrows():
        url, expected_labels = row["URL"], row["Labels"]

        # # Measure time
        # start = time.perf_counter()
        # labels = labeler.moderate_post(url)
        # elapsed = time.perf_counter() - start
        # with open("time_measurement.jsonl", 'a', encoding='utf-8') as f:
        #     f.write(json.dumps(elapsed) + "\n")
        
        # # Measure memory
        # tracemalloc.start()
        # labels = labeler.moderate_post(url)
        # current, peak = tracemalloc.get_traced_memory()
        # tracemalloc.stop()
        # with open("memory_measurement.jsonl", 'a', encoding='utf-8') as f:
        #     f.write(json.dumps([current, peak]) + "\n")

        # # Measure network load
        # def measure_network_for_one_call(url):
        #     # snapshot before
        #     net0 = psutil.net_io_counters()

        #     labels = labeler.moderate_post(url)

        #     # snapshot after
        #     net1 = psutil.net_io_counters()
        #     sent = net1.bytes_sent - net0.bytes_sent
        #     recv = net1.bytes_recv - net0.bytes_recv

        #     return sent, recv, labels
        # sent, recv, labels = measure_network_for_one_call(url)
        # with open("network_measurement.jsonl", 'a', encoding='utf-8') as f:
        #     f.write(json.dumps([sent, recv]) + "\n")
        
        labels = labeler.moderate_post(url)
        if set(labels) == set(expected_labels):
            num_correct += 1
        else:
            print(f"For {url}, labeler produced {labels}, expected {expected_labels}")
            for label in labels:
                label_counter[label] = label_counter.get(label, 0) + 1
        if args.emit_labels and (len(labels) > 0):
            label_post(client, labeler_client, url, labels)

        # For analytics
        with open("labels_test.jsonl", 'a', encoding='utf-8') as f:
            f.write(json.dumps([labels, expected_labels]) + "\n")
    print(f"The labeler produced {num_correct} correct labels assignments out of {total}")
    print(f"Overall ratio of correct label assignments {num_correct/total}")
    print(label_counter)


if __name__ == "__main__":
    main()

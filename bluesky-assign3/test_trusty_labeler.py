"""Script for testing the automated labeler"""

import argparse
import json
import os

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

    urls = pd.read_csv(args.input_urls)
    num_correct, total = 0, urls.shape[0]
    label_counter = {}
    for _index, row in urls.iterrows():
        url, expected_labels = row["URL"], row["Labels"]
        labels = labeler.moderate_post(url)
        if sorted(labels) == sorted(expected_labels):
            num_correct += 1
        else:
            print(f"For {url}, labeler produced {labels}, expected {expected_labels}")
            for label in labels:
                label_counter[label] = label_counter.get(label, 0) + 1
        if args.emit_labels and (len(labels) > 0):
            label_post(client, labeler_client, url, labels)
    print(f"The labeler produced {num_correct} correct labels assignments out of {total}")
    print(f"Overall ratio of correct label assignments {num_correct/total}")
    print(label_counter)


if __name__ == "__main__":
    main()

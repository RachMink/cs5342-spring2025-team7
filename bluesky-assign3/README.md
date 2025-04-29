# Bluesky labeler starter code
You'll find the starter code for Assignment 3 in this repository. More detailed
instructions can be found in the assignment spec.

## The Python ATProto SDK
To build your labeler, you'll be using the AT Protocol SDK, which is documented [here](https://atproto.blue/en/latest/).

## Automated labeler
The bulk of your Part I implementation will be in `automated_labeler.py`. You are
welcome to modify this implementation as you wish. However, you **must**
preserve the signatures of the `__init__` and `moderate_post` functions,
otherwise the testing/grading script will not work. You may also use the
functions defined in `label.py`. You can import them like so:
```
from .label import post_from_url
```

For Part II, you will create a file called `policy_proposal_labeler.py` for your
implementation. You are welcome to create additional files as you see fit.

## Input files
For Part I, your labeler will have as input lists of T&S words/domains, news
domains, and a list of dog pictures. These inputs can be found in the
`labeler-inputs` directory. For testing, we have CSV files where the rows
consist of URLs paired with the expected labeler output. These can be found
under the `test-data` directory.

## Testing
We provide a testing harness in `test-labeler.py`. To test your labeler on the
input posts for dog pictures, you can run the following command and expect to
see the following output:

```
% python test_labeler.py labeler-inputs test-data/input-posts-dogs.csv
The labeler produced 20 correct labels assignments out of 20
Overall ratio of correct label assignments 1.0
```

# Part II documentation
## Data collection and labeling
The input data was generated using get_giveaway_dataset.py, which stores it into
json format. Next, we cleaned it and formatted it into the input format and 
labeled all the posts manually which produces manual-label.csv. Then, we used
clean_data.py to combine our manual labels before separating it into testing 
and training datasets using a 60/40 split. The datasets can be found at 
test-data/labels-cleaned-train.csv and test-data/labels-cleaned-test.csv.

## Trusty Labeler design and testing
policy_proposal_labeler.py holds the core logic of our TrustyLabeler (on bluesky), 
determining whether to put a label and what type of label to add for each post. 
The 3 main components are detect_giveaway(), detect_safe_link(), and detect_bot().

detect_giveaway() uses labeler-inputs/giveaway-words.csv to perform an initial
two-layered filtering based on giveaway words and call-to-action words.

detect_safe_link() checks for links in the post text using regex, as well as in
the facets and embeds uri. It then uses Google's Safe Browsing API to determine
if a link is safe or not, and adds ["Unsafe Link Giveaway"] or ["Safe Link Giveaway"]
labels.

detect_bot() uses the follow_ratio and posts_per_day of the account to determine if 
they are likely a bot or a human, and correspondingly outputs ["Likely Bot Giveaway"]
or ["Likely Human Giveaway"] labels. The thresholds were determined from the training
data, and can be seen both in data_analysis.ipynb as well as the presentation.

The testing script is adapted from the provided testing harness, and can be run 
in a similar manner:

```
% python test_trusty_labeler.py labeler-inputs test-data/labels-cleaned-test.csv
```

## Analysis of results
The results can be analyzed using giveaway_labeler/data_analysis.ipynb.
Accuracy, Precision, Recall and F1 metrics for both the safe link component
and the bot component can be calculated here. For the overall giveaway 
component, we did it in the excel sheet after manually labeling the dataset.

We also measured the efficiency and performance of the code. In our 
test_trusty_labeler.py, we have commented out the code for measuring time 
taken, memory and network for each moderate_post() call. These can be run
and produces time_measurement.jsonl, memory_measurement.jsonl and 
network_measurement.jsonl respectively. We have also performed data analysis
in data_analysis.ipynb, and the results are further discussed in our presentation.
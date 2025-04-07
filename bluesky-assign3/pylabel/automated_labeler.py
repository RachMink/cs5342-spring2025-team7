"""Implementation of automated moderator"""

from typing import List
from atproto import Client
from dotenv import load_dotenv
import os
import pprint
import pandas as pd
from .label import post_from_url


load_dotenv(override=True)
USERNAME = os.getenv("USERNAME")
PW = os.getenv("PW")

client = Client()
profile = client.login(USERNAME, PW)
pprint.pprint(profile.__dict__)

T_AND_S_LABEL = "t-and-s"
DOG_LABEL = "dog"
THRESH = 0.3

class AutomatedLabeler:
    """Automated labeler implementation"""

    def __init__(self, client: Client, input_dir):
        self.client = client

        #Read domains and words files for t-and-s label
        domains_df = pd.read_csv('./labeler-inputs/t-and-s-domains.csv')
        self.domains = {domain.lower(): True for domain in domains_df['Domain'].dropna()}
        words_df = pd.read_csv('./labeler-inputs/t-and-s-words.csv')
        self.words = {word.lower(): True for word in words_df['Word'].dropna()}

        #Read news domains file for news label
        news_domains_df = pd.read_csv('./labeler-inputs/news-domains.csv')
        self.news_domains = dict(zip(news_domains_df['Domain'], news_domains_df['Source']))

    def moderate_post(self, url: str) -> List[str]:
        """
        Apply moderation to the post specified by the given url
        """
        #Labeling logic
        labels = []
        #Milestone 2: Apply "t-and-s" label
        labels.extend(self.detect_t_and_s(url))
        #Milestone 3: Apply "news" label
        labels.extend(self.detect_news(url))

        return labels

    #Milestone 2: Label posts with T&S words and domains
    def find_t_and_s_matches(self, text: str) -> dict:
        """Find matches in text from both domains and words lists"""
        domain_matches = [domain for domain in self.domains if domain in text]
        word_matches = [word for word in self.words if word.lower() in text]
        
        #Return both domain and word matches
        return {
            'domain_matches': domain_matches,
            'word_matches': word_matches
        }
    
    def detect_t_and_s(self, url: str) -> List[str]:
        """Detect T&S posts and label them using find_t_and_s_matches()"""
        post = post_from_url(self.client, url)
        post_text = post.value.text.lower() #Grab text and convert to lowercase for matching
        # print(post_text)

        #Find matches
        matches = self.find_t_and_s_matches(post_text)
        # print(matches)
        if matches['domain_matches'] or matches['word_matches']:
            return [T_AND_S_LABEL]
        else:
            return []
    
    #Milestone 3: Cite your sources
    def find_news_matches(self, text: str) -> dict:
        """Find matches in text from news domain list"""
        news_matches = [domain for domain in self.news_domains if domain in text]
        
        #Return both news domain matches
        return {
            'domain_matches': news_matches,
        }
    
    def detect_news(self, url: str) -> List[str]:
        """Detect news posts and label them using find_news_matches()"""
        post = post_from_url(self.client, url)
        post_text = post.value.text.lower() #Grab text and convert to lowercase for matching

        #Find matches
        matches = self.find_news_matches(post_text)
        if matches['domain_matches']:
            return [self.news_domains[matches['domain_matches'][0]]]
        else:
            return []
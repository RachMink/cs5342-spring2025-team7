"""Implementation of automated moderator"""

from typing import List
from atproto import Client
from dotenv import load_dotenv
import os
import pprint
import pandas as pd
from .label import post_from_url
from PIL import Image
from io import BytesIO
import requests
from perception import hashers


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
        #Milestone 4: Apply "dog" label
        labels.extend(self.find_dog(url))
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
        
    #Milestone 4: Dog labeler
    def parse_handle_from_url(self, url: str):
        """Extract handle from a Bluesky post URL in format "https://bsky.app/profile/handle.bsky.social/post/postid"""
        parts = url.split("/")
        handle = parts[-3]
        return handle
    
    def get_did_from_handle(self, handle):
        """Get DID from handle using ATProto API"""
        url = f"https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle={handle}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['did']
        else:
            print(f"Error resolving DID for {handle}")
            return None
        
    def construct_url(self, url):
        """Construct URL to get image. URL takes the form: "https://cdn.bsky.app/img/feed_thumbnail/plain/" + {their DID} + {blob CID}@jpeg"""
        initial_url = "https://cdn.bsky.app/img/feed_thumbnail/plain/"

        #Get DID
        handle = self.parse_handle_from_url(url)
        did = self.get_did_from_handle(handle)

        #Get blob CID
        post = post_from_url(client, url)
        # if hasattr(post.value, 'embed') and post.value.embed is not None:
            # Check if embed has images
        if hasattr(post.value.embed, 'images') and post.value.embed.images:
            blob_CID = post.value.embed.images[0].image.ref.link
        else:
            return None

        #Construct final URL
        final_url = initial_url + did + "/" + blob_CID + "@jpeg"
        return final_url
    
    def download_image_from_url(self, url):
        """Download image from URL"""
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()  #Raises error if image failed to download
            image = Image.open(BytesIO(response.content))
            return image
        except Exception as e:
            print(f"Error downloading image from {url}: {e}")
            return None
        
    def find_dog(self, url):
        """Find out if the image is a dog using pHash and THRESH"""
        image_url = self.construct_url(url)
        if image_url is None:
            return []
        image_file = self.download_image_from_url(image_url)

        hasher = hashers.PHash()
        original_image_hash = hasher.compute(image_file)

        #Directory containing dog images
        dog_images_dir = "labeler-inputs/dog-list-images"

        #Compare with each dog image
        for filename in os.listdir(dog_images_dir):
            if filename.endswith(".jpg"):
                image_path = os.path.join(dog_images_dir, filename)
                comparison_image = Image.open(image_path)
                comparison_hash = hasher.compute(comparison_image)
                distance = hasher.compute_distance(original_image_hash, comparison_hash)
                if distance < THRESH:
                    return [DOG_LABEL]

        #If no match, return no dog label
        return []
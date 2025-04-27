from atproto import Client
from dotenv import load_dotenv
import os
import pprint
import random
import time
import json
import pandas as pd
import re

load_dotenv(override=True)
USERNAME = os.getenv("USERNAME")
PW = os.getenv("PW")

client = Client()
profile = client.login(USERNAME, PW)
pprint.pprint(profile.__dict__)

def search_users_by_keyword(keyword, limit=20):
    results = client.app.bsky.actor.search_actors({'q': keyword, 'limit': limit})
    return [user['handle'] for user in results['actors']]

def get_user_posts(handle, limit=3):
    try:
        actor = client.com.atproto.identity.resolve_handle({'handle': handle})
        feed = client.app.bsky.feed.get_author_feed({'actor': actor['did'], 'limit': limit})
        return [{
            'user': handle,
            'text': post['post']['record']['text'],
            'uri': post['post']['uri'],
            'cid': post['post']['cid']
        } for post in feed['feed']]
    except Exception as e:
        print(f"Failed on {handle}: {e}")
        return []

def get_random_posts():
    KEYWORDS = [
        "the", "life", "news", "day", "art", "love", "fun", 
        "you", "post", "time", "and", "world", "game", "travel",
        "music", "photo", "food", "coffee", "fashion", "tech", "science",
        "health", "nature", "sunset", "sunrise", "travel", "code", "design",
        "film", "video", "story", "humor", "fitness", "yoga", "pets", "cats",
        "dogs", "meme", "inspiration", "mindfulness", "book", "poetry",
        "cooking", "sports", "newsfeed", "tutorial", "climate", "culture"
    ]
    POSTS_TO_COLLECT = 6000
    POSTS_PER_USER = 3
    COLLECTED_POSTS = []
    random.shuffle(KEYWORDS)

    for keyword in KEYWORDS:
        if len(COLLECTED_POSTS) >= POSTS_TO_COLLECT:
            break
        handles = search_users_by_keyword(keyword)
        random.shuffle(handles)
        
        for handle in handles:
            if len(COLLECTED_POSTS) >= POSTS_TO_COLLECT:
                break
            posts = get_user_posts(handle, limit=POSTS_PER_USER)
            COLLECTED_POSTS.extend(posts)
            time.sleep(0.5)  # be nice to the API

    # Save to JSON
    with open('bluesky_random_posts.json', 'w') as f:
        json.dump(COLLECTED_POSTS, f, indent=2)
    return COLLECTED_POSTS

def get_giveaway_posts():
    df = pd.read_csv("./labeler-inputs/giveaway-words.csv")

    # Extract the first column
    words = df['Words'].dropna()
    call_to_action = df['call-to-action'].dropna()

    # Print or process
    GIVEAWAY_WORDS = words.tolist()
    CTA = call_to_action.tolist()
    print(GIVEAWAY_WORDS)
    print(CTA)

    GIVEAWAY_POSTS = []

    random.shuffle(GIVEAWAY_WORDS)

    for keyword in GIVEAWAY_WORDS:
        response = client.app.bsky.feed.search_posts({'q': keyword, 'limit': 10})
        for post in response.posts:
            user = post.author.handle
            text = post.record.text
            uri = post.uri
            cid = post.cid
            # possibly collect replies down the line
            GIVEAWAY_POSTS.append({
                'user': user,
                'text': text,
                'uri': uri,
                'cid': cid
            })

    # Save to JSON
    with open('bluesky_giveaway_posts.json', 'w') as f:
        json.dump(GIVEAWAY_POSTS, f, indent=2)

    CTA_GIVEAWAY_POSTS = []
    for post in GIVEAWAY_POSTS:
        for cta in CTA:
            if re.search(rf"\b{re.escape(cta)}\b", post['text'], re.IGNORECASE):
                CTA_GIVEAWAY_POSTS.append(post)
                break

    with open('bluesky_confirmed_giveaway_posts.json', 'w') as f:
        json.dump(CTA_GIVEAWAY_POSTS, f, indent=2)
    
    return GIVEAWAY_POSTS, CTA_GIVEAWAY_POSTS

def train_test_split_list(items, train_frac=0.6, seed=42):
    rnd = random.Random(seed)
    rnd.shuffle(items)
    cutoff = int(len(items) * train_frac)
    return items[:cutoff], items[cutoff:]

def main():
    COLLECTED_POSTS = get_random_posts()
    GIVEAWAY_POSTS, CTA_GIVEAWAY_POSTS = get_giveaway_posts()

    COMBINED_POSTS = GIVEAWAY_POSTS + COLLECTED_POSTS
    with open('bluesky_combined_posts.json', 'w') as f:
        json.dump(COMBINED_POSTS, f, indent=2)

    print(f"Collected {len(COMBINED_POSTS)} posts.")

    # Split into test and train sets (60-40 split)
    with open('bluesky_random_posts.json', 'r') as f:
        COLLECTED_POSTS = json.load(f)

    with open('bluesky_giveaway_posts.json', 'r') as f:
        GIVEAWAY_POSTS = json.load(f)

    with open('bluesky_confirmed_giveaway_posts.json', 'r') as f:
        CTA_GIVEAWAY_POSTS = json.load(f)

    # Remove CTA_GIVEAWAY_POSTS from GIVEAWAY_POSTS so there aren't repeats in the test set
    confirmed_ids = { post['cid'] for post in CTA_GIVEAWAY_POSTS }
    remainder = [ post for post in GIVEAWAY_POSTS if post['cid'] not in confirmed_ids ] 
    remainder_train, remainder_test = train_test_split_list(remainder)
    confirmed_giveaway_train, confirmed_giveaway_test = train_test_split_list(CTA_GIVEAWAY_POSTS)
    random_dataset_train, random_dataset_test = train_test_split_list(COLLECTED_POSTS)

    train_set = random_dataset_train + confirmed_giveaway_train + remainder_train
    test_set = random_dataset_test + confirmed_giveaway_test + remainder_test
    print("Train set:", len(train_set))
    print("Test set:", len(test_set))

    #Convert to input csv format with a link and a label
    rows = []
    for post in train_set:
        uri = post['uri']
        # uri looks like: "at://did:plc:…/postid"
        user, post_id = uri.split('/')[2], uri.split('/')[-1]
        url = f"https://bsky.app/profile/{user}/post/{post_id}"
        label = ["giveaway"] if post['cid'] in confirmed_ids else []
        rows.append((url, label))

    df = pd.DataFrame(rows, columns=["URL", "Label"])
    df.to_csv("input-posts-giveaway-train.csv", index=False)

    rows = []
    for post in test_set:
        uri = post['uri']
        # uri looks like: "at://did:plc:…/postid"
        user, post_id = uri.split('/')[2], uri.split('/')[-1]
        url = f"https://bsky.app/profile/{user}/post/{post_id}"
        label = ["giveaway"] if post['cid'] in confirmed_ids else []
        rows.append((url, label))

    df = pd.DataFrame(rows, columns=["URL", "Label"])
    df.to_csv("input-posts-giveaway-test.csv", index=False)

if __name__ == "__main__":
    main()
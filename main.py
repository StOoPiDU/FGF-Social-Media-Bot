import praw
import os
import json
from dotenv import load_dotenv
from typing import List, Optional
from praw.exceptions import RedditAPIException, ClientException
from prawcore.exceptions import RequestException, ResponseException
from atproto import Client, client_utils
import tweepy
from tweepy.errors import TweepyException
import requests

load_dotenv()

# Init Reddit
try:
    reddit = praw.Reddit(client_id=os.getenv('CLIENT_ID'),
                        client_secret=os.getenv('CLIENT_SECRET'),
                        user_agent=os.getenv('USER_AGENT'),
                        # refresh_token=os.getenv('REFRESH_TOKEN')
                        )

except Exception as e:
    print(f"Reddit API failure: {e}")
    exit(1)

subreddit = reddit.subreddit("FreeGameFindings")
json_file = "saved_posts.json"

def get_reddit_posts(post_count: int) -> Optional[List]:
    skip_flairs = ["modpost","fgfGiveaway"]
                                # reversed(list works but then the typing is mad
    new_subreddit_posts: List = list(reversed(list(subreddit.new(limit=post_count))))
    filtered_subreddit_posts: List = list(post for post in new_subreddit_posts if post.link_flair_css_class not in skip_flairs)


    try:
        with open(json_file, "r", encoding="utf8") as f:
            saved_data = json.load(f)
    except FileNotFoundError:
        saved_data = []

    try:
        saved_ids = set(post['id'] for post in saved_data)
        new_data = [
            {"id": post.id,
             # "title": post.title # No title trim
             "title": (post.title[:165] + "...") if len(post.title) > 165 else post.title} # Title trim
            for post in filtered_subreddit_posts
            if post.id not in saved_ids
        ]

        if new_data:
            saved_data.extend(new_data)
            with open(json_file, "w", encoding="utf8") as f:
                json.dump(saved_data, f, indent=4)

            print(f"Saving {new_data}")
            return new_data
        else:
            print ("No new posts")
            return None

    except (RedditAPIException, ClientException, ResponseException, RequestException) as e:
        print(f"Reddit API error (Reddit might be down): {e}")

    except Exception as e:
        print(f"An error occurred: {e}")

def post_to_bluesky(posts: List):
    try:
        # Init Blue Sky
        client = Client()
        client.login(os.getenv("BS_HANDLE"), os.getenv("BS_PASSWORD"))

        for post in posts:
            print(f"Blue Sky: Posting {post["title"]}")

            if "PSA" in post["title"].upper():
                text = (client_utils.TextBuilder().text(f"New PSA live on FGF:\n{post["title"]}\n\n")
                        .tag("#FGF ", "FGF").tag("#FreeGameFindings\n\n", "FreeGameFindings")
                        .link(f"https://redd.it/{post["id"]}", f"https://redd.it/{post["id"]}"))
            else:
                text = (client_utils.TextBuilder().text(f"{post["title"]} is free! See the /r/FreeGameFindings thread below.\n\n")
                        .tag("#FGF ", "FGF").tag("#FreeGameFindings ", "FreeGameFindings").tag("#Free\n\n", "Free")
                        .link(f"https://redd.it/{post["id"]}", f"https://redd.it/{post["id"]}"))

            try:
                client.send_post(text)
            except Exception as e:
                print(f"Blue Sky error ({post['title']}): {e}")

    except Exception as e:
        print(f"Exception: {e}")

def post_to_twitter(posts: List):
    try:
        # Init Twitter
        client = tweepy.Client(
            consumer_key=os.getenv('T_CONSUMER_KEY'),
            consumer_secret=os.getenv('T_CONSUMER_SECRET'),
            access_token=os.getenv('T_ACCESS_TOKEN'),
            access_token_secret=os.getenv('T_ACCESS_TOKEN_SECRET')
        )

        for post in posts:
            print(f"Twitter: Posting {post["title"]}")

            if "PSA" in post["title"].upper():
                text = (f"New PSA live on FGF:\n{post["title"]}\n\n"
                        f"#FGF #FreeGameFindings\n\n"
                        f"https://redd.it/{post["id"]}")
            else:
                text = (f"{post["title"]} is #free! See the /r/FreeGameFindings thread below.\n\n"
                        f"#FGF #FreeGameFindings\n\n"
                        f"https://redd.it/{post["id"]}")

            try:
                client.create_tweet(text=text)
            except TweepyException as t_e:
                print(f"Tweet error ({post['title']}): {t_e}")

    except Exception as e:
        print(f"Exception: {e}")

def post_to_facebook(posts: List):
    try:
        # Init Facebook
        app_id = os.getenv('FB_APP_ID')
        app_secret = os.getenv('FB_APP_SECRET')
        access_token = os.getenv('FB_ACCESS_TOKEN') # This token expires bi-monthly
        page_id = os.getenv('FB_PAGE_ID')

        url = f"https://graph.facebook.com/v22.0/{page_id}/feed"

        for post in posts:
            print(f"Facebook: Posting {post["title"]}")

            if "PSA" in post["title"].upper():
                text = (f"New PSA live on FGF:\n{post["title"]}\n\n"
                        f"#FGF #FreeGameFindings\n\n"
                        f"https://redd.it/{post["id"]}")
            else:
                text = (f"{post["title"]} is #free! See the /r/FreeGameFindings thread below.\n\n"
                        f"#FGF #FreeGameFindings\n\n"
                        f"https://redd.it/{post["id"]}")

            if text:
                data = {
                    "message": text,
                    "access_token": access_token
                }

                try:
                    response = requests.post(url, params=data)

                except Exception as e:
                    print(f"Facebook Error ({post['title']}): {e}")
                    # print(response.text)

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == '__main__':
    reddit_posts = get_reddit_posts(5)

    if reddit_posts is not None:
        print("reddit_posts not empty.")
        post_to_bluesky(reddit_posts)
        post_to_twitter(reddit_posts)
        post_to_facebook(reddit_posts)
import subprocess
import time
import signal
import requests
import requests.auth
import json
import os
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import secret  # Reddit API credentials


class RedditAuth:

    def __init__(self):
        pass

    @staticmethod
    def get_auth_code():
        payload = secret.payload
        cmd = 'python -m http.server'
        process = subprocess.Popen(cmd)  # open localhost http server:

        # get the required code from the response url
        url = f'https://www.reddit.com/api/v1/authorize?client_id={payload.get("client_id")}&response_type=code&state=' \
              f'{payload.get("state")}&redirect_uri={payload.get("redirect_uri")}&duration=' \
              f'{payload.get("duration")}&scope={payload.get("scope")}'

        driver = webdriver.Chrome(ChromeDriverManager().install())
        driver.get(url)
        codeurl = ''
        i = 0
        while i == 0:
            codeurl = driver.current_url
            time.sleep(2)
            if ':8080/?state=MYSTATESTRING' in codeurl:
                codeurl = str(driver.current_url)
                i = 1
            else:
                pass
        code_intermediate1 = codeurl.split("=")[2]
        code = code_intermediate1.split("#")[0]
        process.send_signal(signal.SIGTERM)    # terminate server
        print("successfully obtained authorization code")
        return code

    @staticmethod
    def get_token(code):
        payload = secret.payload
        payload['code'] = str(code)
        client_auth = requests.auth.HTTPBasicAuth(payload.get('client_id'), payload.get('client_secret'))
        post_data = f'grant_type=authorization_code&code={code}&redirect_uri={payload.get("redirect_uri")}'
        r = requests.post('https://www.reddit.com/api/v1/access_token', auth=client_auth, data=post_data)
        response = r.json()
        token = response.get('access_token')
        return token

    @staticmethod
    def reddit_scraper(token, after, username):
        params = {'limit': '100'}
        if len(after) > 1:
            params['after'] = after

        url = f'https://oauth.reddit.com/u/{username}/saved'
        headers = {"User-Agent": "SavedSorter/0.1 by ekindeveli0", 'Authorization': f'bearer {token}'}
        r = requests.get(url, headers=headers, params=params)
        print(f"Fetching posts...")  # to make sure Response is 200, eg successful fetch
        response = json.loads(r.text)
        with open("response.json", "w+", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False, indent=4)

    @staticmethod
    def saved_sorter():
        if os.path.isfile('saved.json'):
            with open('saved.json', "r", encoding="utf-8") as f:
                categ = json.load(f)
        else:
            categ = {}
        with open('response.json', encoding="utf=8") as json_file:
            rsp = json.load(json_file)
            for p in rsp['data']['children']:
                sr_array = []
                subreddit = p.get('data', {}).get('subreddit')
                name = p.get('data', {}).get('name')
                if name.startswith("t1_"):
                    title = p.get('data', {}).get('link_title')
                    url = p.get('data', {}).get('link_permalink')
                    permalink = url
                elif name.startswith("t3_"):
                    title = p.get('data', {}).get('title')
                    url = p.get('data', {}).get('url')
                    permalink = p.get('data', {}).get('permalink')
                    permalink = 'https://www.reddit.com' + permalink
                info = [name, title, permalink, url]
                if permalink == url:
                    info.remove(permalink)
                sr_array.append(info)
                if subreddit in categ:
                    if sr_array[0] not in categ[subreddit]:
                        categ[subreddit].append(sr_array[0])
                else:
                    categ[subreddit] = sr_array
        # add the created dict to the database
        with open("saved.json", "w+", encoding="utf-8") as f:
            json.dump(categ, f, ensure_ascii=False, indent=4)
        return name


kod = RedditAuth.get_auth_code()
token_response = None
while token_response is None:
    token_response = RedditAuth.get_token(kod)
    time.sleep(1)
t = 0
aftr = ""
usrname = input("Enter the username of the account for which you'd like to sort saved posts, \n"
                "this username must match the one that gave permission: ")
while t == 0:
    try:
        RedditAuth.reddit_scraper(token_response, aftr, usrname)
        aftr = RedditAuth.saved_sorter()
        time.sleep(1)
    except UnboundLocalError:
        print("Sorting Completed. Exiting Script.")
        t = 1

if os.path.isfile("response.json"):
    os.remove("response.json")


import calendar
import hashlib
import json
import os
import requests
import feedparser

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
USERS = [u.strip().lstrip("@") for u in os.environ["X_USERS"].split(",") if u.strip()]
HEADERS = {"User-Agent": "Mozilla/5.0"}
STATE = "seen.json"
POSTS = "posts.json"

try:
    with open(STATE) as f:
        seen = json.load(f)
except Exception:
    seen = {}

try:
    with open(POSTS) as f:
        by_link = {p["link"]: p for p in json.load(f)}
except Exception:
    by_link = {}

def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=20,
    )
    if r.status_code != 200:
        print("Telegram refused the message:", r.status_code)
        return False
    return True

for user in USERS:
    key = hashlib.sha256(user.lower().encode()).hexdigest()[:10]
    try:
        r = requests.get(f"https://nitter.mie.foundation/{user}/rss", headers=HEADERS, timeout=20)
        feed = feedparser.parse(r.text)
        ids = [e.id for e in feed.entries]
        if not ids:
            print("No posts returned for account", key)
            continue
        for e in feed.entries:
            link = e.link.split("#")[0].replace("nitter.mie.foundation", "x.com")
            ts = calendar.timegm(e.published_parsed) if e.get("published_parsed") else 0
            by_link[link] = {"user": user, "text": e.title, "link": link, "time": ts}
        if key not in seen:
            seen[key] = ids
            print("First run for account", key, "- remembering", len(ids), "posts")
            continue
        for e in reversed(feed.entries):
            if e.id not in seen[key]:
                if send("New post from @" + user + ":\n" + e.title + "\n" + e.link):
                    seen[key].append(e.id)
        seen[key] = seen[key][-100:]
        print("Checked account", key, "-", len(ids), "posts")
    except Exception as err:
        print("Error for account", key, type(err).__name__)

with open(STATE, "w") as f:
    json.dump(seen, f)

latest = sorted(by_link.values(), key=lambda p: p["time"], reverse=True)[:60]
with open(POSTS, "w") as f:
    json.dump(latest, f)
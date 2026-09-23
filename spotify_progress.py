import os
from dotenv import load_dotenv, dotenv_values 
import string, secrets, hashlib, base64
import urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

captured_code = "N/A"

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global captured_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
            captured_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
    
    def log_message(self, format, *args):
        return

server = HTTPServer(("127.0.0.1", 8080), CallbackHandler)

load_dotenv() 
client_id = os.getenv("client_id")
redir_url = os.getenv("redirect_url")

def gen_code_verifier():
    alphabet = string.ascii_letters + string.digits
    code_verifier = ''.join(secrets.choice(alphabet) for _ in range(64))
    return code_verifier

# hash via SHA-256
def gen_code_challenge(code_verifier):
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return code_challenge

code_verifier = gen_code_verifier()
code_challenge = gen_code_challenge(code_verifier)
# scope = "playlist-read-private"
scope = "user-library-read"

params = {
    "response_type": "code",
    "client_id": client_id,
    "scope": scope,
    "code_challenge_method": "S256",
    "code_challenge": code_challenge,
    "redirect_uri": redir_url,
}

base_auth_url = "https://accounts.spotify.com/authorize"
auth_url = f"{base_auth_url}?{urllib.parse.urlencode(params)}"

webbrowser.open(auth_url)
server.handle_request()
print("Extracted code: ", captured_code)

## exchange code for access token
# https://accounts.spotify.com/api/token
headers = {'Content-Type': 'application/x-www-form-urlencoded'}
payload = {
    'client_id': client_id,
    'grant_type': 'authorization_code',
    'code': captured_code,
    'redirect_uri': redir_url,
    'code_verifier': code_verifier
}
x = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=payload)
data = x.json()
access_token = data.get("access_token")
print(access_token)

headers = {"Authorization": f"Bearer {access_token}"}
liked_songs_playlist_url = os.getenv("liked_songs_playlist_url")
completed_playlist_url = os.getenv("completed_playlist_url")

songs_assigned = [] # track IDs of songs inside liked
total_tracks = 0
total_assgn_tracks = 0

while completed_playlist_url:
    res = requests.get(completed_playlist_url, headers=headers).json()
    if "items" not in res:
        print("Error:", res)
        break

    for item in res["items"]:
        track = item.get("item")
        if track:
            songs_assigned.append(track.get("id"))
    completed_playlist_url = res.get("next")

print("Assigned songs length: ", len(songs_assigned))


while liked_songs_playlist_url:
    res = requests.get(liked_songs_playlist_url, headers=headers).json()
    
    if "items" not in res:
        print("Error:", res)
        break
        
    for item in res["items"]:
        track = item.get("track")
        if track:
            total_tracks += 1
            if (track.get("id")) in songs_assigned:
                total_assgn_tracks += 1
    liked_songs_playlist_url = res.get("next")  # Pagination to fetch all liked songs


print(f"Total Liked Songs: {total_tracks}")
try:
    completion_pcntg = (total_assgn_tracks / total_tracks) * 100
    print(f"Completion Percentage: {completion_pcntg:.2f}%")
except ZeroDivisionError:
    print("Error: 0 tracks have been assigned to done")
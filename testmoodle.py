import os
import requests
from urllib.parse import unquote

URL = "https://elearning.umn.ac.id/login/index.php"

DEFAULTS = {
  "anchor": "",
  "logintoken": "BEDnsqjFkWkrJpTAGbKbHvpVLemx65pm",
  "username": os.getenv("MOODLE_USERNAME", "placeholder%40student.umn.ac.id"),
  "password": os.getenv("MOODLE_PASSWORD", "passwordtemplate"),
}

HEADERS = {
  "Accept-Language": "en-US,en;q=0.9",
  "Origin": "https://elearning.umn.ac.id",
  "Content-Type": "application/x-www-form-urlencoded",
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
  "Referer": "https://elearning.umn.ac.id/login/index.php",
}

COOKIE_STRING = os.getenv("MOODLE_COOKIE_STRING", "_ga=GA1.1.777431119.1774803230; cf_clearance=zxORiAEVHwkTb_Ho44_gcAEodnUhyo1z1yMfeLNek0w-1776068748-1.2.1.1-sC8JaiY2x_9c0Zyk.BRqCx6KJOzr9Todfk66_XtWMjeauBI1t_WmDsMHyHWsvgem6IQNOXDCm.nRMAGcuSiwnZ6lkhbPh6TT54ZaK2_hzSbH_aeFBzfl38MmQJWSE3n.nSvTraLQYghKxUEr_hT_2Fgv3faY_2CSt9VuPr2MGMYEI_kKjHWTBU_YZNr1KmxhLRuwg8SJ16plCFSgdrvNMq8pISkIuMCOrY431s_r8UgwrBZeKKkNkL.Zh7_XcWPNrFx0IavVJcZa2YoNj07ajtOsD5i22ev6AB.bKapmyYA66GjhmBEJ3PY_X37fSNN6KlzrvBmo1S7Opm7djLWcIg; MoodleSession2526=f0fvogi3vcej4melj8sc4ohc98; _ga_JY9M6JWD05=GS2.1.s1777699648$o6$g1$t1777699665$j43$l0$h0")

def parse_cookie_string(cookie_str):
  cookies = {}
  if not cookie_str:
    return cookies
  for part in cookie_str.split(";"):
    if "=" in part:
      k, v = part.split("=", 1)
      cookies[k.strip()] = v.strip()
  return cookies

def main():
  data = {
    "anchor": DEFAULTS["anchor"],
    "logintoken": DEFAULTS["logintoken"],
    # reencode incase username is URL-encoded (like contains %40 for @)
    "username": unquote(DEFAULTS["username"]) if "%" in DEFAULTS["username"] else DEFAULTS["username"],
    "password": DEFAULTS["password"],
  }

  session = requests.Session()
  session.headers.update(HEADERS)
  cookies = parse_cookie_string(COOKIE_STRING)
  if cookies:
    session.cookies.update(cookies)

  print(f"Posting to {URL} with username={data['username']}")
  resp = session.post(URL, data=data, allow_redirects=True, timeout=30)

  print("Status:", resp.status_code)
  print("Final URL:", resp.url)

  """
  with open("login_response.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
  """

  logged_in = False
  if "login/index.php" not in resp.url:
    logged_in = True
  if "logout" in resp.text.lower():
    logged_in = True

  print("Login successful:" if logged_in else "Login likely failed. See login_response.html")
  print("Session cookies:")
  for k, v in session.cookies.items():
    print(f"  {k} = {v}")

if __name__ == "__main__":
  main()

import os
import re
import json
import requests
from urllib.parse import unquote, quote_plus
import state as state_mod


LOGIN_URL = "https://elearning.umn.ac.id/login/index.php"
HOME_URL = "https://elearning.umn.ac.id/"

# Environment / defaults
USERNAME = os.getenv("MOODLE_USERNAME", "template%40student.umn.ac.id")
PASSWORD = os.getenv("MOODLE_PASSWORD", "passwordtemplate")
COOKIE_STRING = os.getenv("MOODLE_COOKIE_STRING", "")
FALLBACK_SESSKEY = os.getenv("MOODLE_SESSKEY", "YEyYksMOSD")

AJAX_BODY = [
  {
    "index": 0,
    "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
    "args": {
      "offset": 0,
      "limit": 240,
      "classification": "customfield",
      "sort": "fullname",
      "customfieldname": "semester",
      "customfieldvalue": "2",
    },
  }
]


def parse_cookie_string(cookie_str: str):
  cookies = {}
  if not cookie_str:
    return cookies
  parts = [p.strip() for p in cookie_str.split(";") if p.strip()]
  for p in parts:
    if "=" in p:
      k, v = p.split("=", 1)
      cookies[k.strip()] = v.strip()
  return cookies


def extract_logintoken(html: str):
  m = re.search(r'<input[^>]+name="logintoken"[^>]+value="([^"]+)"', html)
  if m:
    return m.group(1)
  m = re.search(r'name=["\']logintoken["\']\s+value=["\']([^"\']+)["\']', html)
  if m:
    return m.group(1)
  return None


def extract_sesskey(html: str):
  # extract M.cfg JSON blob (contains sesskey on many Moodle pages)
  m = re.search(r'M\.cfg\s*=\s*(\{.*?\})\s*;', html, re.S)
  if m:
    try:
      cfg_text = m.group(1)
      # normalize JS-style JSON (should already be JSON-compatible)
      cfg = json.loads(cfg_text)
      if isinstance(cfg, dict) and "sesskey" in cfg:
        return cfg["sesskey"]
    except Exception:
      pass

  # Try multiple common patterns for sesskey in page JS or forms
  m = re.search(r'sesskey\s*[:=]\s*["\']([A-Za-z0-9_-]{6,})["\']', html)
  if m:
    return m.group(1)
  m = re.search(r'name="sesskey"\s+value="([A-Za-z0-9_-]{6,})"', html)
  if m:
    return m.group(1)
  return None


def login_and_get_session():
  session = requests.Session()
  session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible)",
    "Referer": LOGIN_URL,
  })

  if COOKIE_STRING:
    session.cookies.update(parse_cookie_string(COOKIE_STRING))

  # Fetch login page to get dynamic logintoken
  try:
    r = session.get(LOGIN_URL, timeout=20)
  except Exception as e:
    print("Failed to GET login page:", e)
    return None, None

  token = extract_logintoken(r.text)
  if token:
    print("Found dynamic logintoken")
  else:
    print("No logintoken found on login page; falling back to empty token")
    token = ""

  data = {
    "anchor": "",
    "logintoken": token,
    "username": unquote(USERNAME) if "%" in USERNAME else USERNAME,
    "password": PASSWORD,
  }

  # Post login
  try:
    resp = session.post(LOGIN_URL, data=data, allow_redirects=True, timeout=30)
  except Exception as e:
    print("Login POST failed:", e)
    return None, None

  # Save debug HTML
  with open("login_response.html", "w", encoding="utf-8") as fh:
    fh.write(resp.text)

  logged_in = False
  if "login/index.php" not in resp.url:
    logged_in = True
  if "logout" in resp.text.lower():
    logged_in = True

  if logged_in:
    print("Login appears successful")
  else:
    print("Login may have failed; check login_response.html or provide cookie string")

  page_html = resp.text
  if not page_html or len(page_html) < 100:
    try:
      r2 = session.get(HOME_URL, timeout=20)
      page_html = r2.text
    except Exception:
      page_html = ""

  sesskey = extract_sesskey(page_html)
  if sesskey:
    print("Extracted sesskey:", sesskey)
  else:
    print("Could not extract sesskey; will try fallback or ask user to provide MOODLE_SESSKEY")
    sesskey = FALLBACK_SESSKEY

  # Print cookies for user
  print("Session cookies:")
  for k, v in session.cookies.items():
    print(f"  {k} = {v}")

  return session, sesskey


def fetch_courses(session: requests.Session, sesskey: str):
  service_name = "core_course_get_enrolled_courses_by_timeline_classification"
  info_param = quote_plus(service_name)
  url = f"https://elearning.umn.ac.id/lib/ajax/service.php?sesskey={sesskey}&info={info_param}"

  headers = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": HOME_URL,
  }

  try:
    resp = session.post(url, data=json.dumps(AJAX_BODY), headers=headers, timeout=30)
  except Exception as e:
    print("AJAX request failed:", e)
    return None

  with open("courses_response.json", "w", encoding="utf-8") as fh:
    try:
      json.dump(resp.json(), fh, ensure_ascii=False, indent=2)
    except Exception:
      fh.write(resp.text)

  try:
    return resp.json()
  except Exception:
    return None


def extract_course_links(data):
  # Find courses array in response
  courses = None
  if isinstance(data, list):
    for item in data:
      if isinstance(item, dict) and isinstance(item.get("data"), dict) and "courses" in item.get("data"):
        courses = item["data"]["courses"]
        break
    if courses is None and len(data) > 0 and isinstance(data[0], dict) and "courses" in data[0]:
      courses = data[0]["courses"]
  elif isinstance(data, dict):
    if "courses" in data:
      courses = data["courses"]

  if not courses:
    print("No courses array found in response")
    return []

  result = []
  for c in courses:
    name = c.get("fullname") or c.get("shortname") or str(c.get("id"))
    # common link fields
    link = c.get("url") or c.get("viewurl") or c.get("courseurl")
    if not link and c.get("id"):
      link = f"https://elearning.umn.ac.id/course/view.php?id={c.get('id')}"
    result.append({"name": name, "link": link})
  return result


def main():
  session, sesskey = login_and_get_session()
  if not session:
    print("Unable to create session; aborting")
    return

  data = fetch_courses(session, sesskey)
  if data is None:
    print("Failed to fetch or parse courses response; see courses_response.json")
    return

  links = extract_course_links(data)
  if not links:
    print("No course links extracted; check courses_response.json")
    return

  print(f"Found {len(links)} courses (showing up to 50):")
  for c in links[:50]:
    print(" -", c["name"], "->", c["link"])

  # Persist into student_state.json via state.py
  try:
    st = state_mod.load_state()
    st['courses'] = links
    state_mod.save_state(st)
    print(f"Saved {len(links)} courses into {state_mod.STATE_FILE}")
  except Exception as e:
    print("Failed to save courses into state:", e)


if __name__ == "__main__":
  main()

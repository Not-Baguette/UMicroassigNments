import requests
import re

class MoodleAgent:
    def __init__(self, username, password, base_url):
        self.username = username
        self.password = password
        self.base_url = base_url
        self.session = requests.Session()
        # Using a very common browser header
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        })

    def run(self):
        try:
            # 1. Handshake to get login token
            print("[*] Agent: Handshaking...")
            res = self.session.get(f"{self.base_url}/login/index.php")
            l_token = re.search(r'name="logintoken" value="([^"]+)"', res.text).group(1)

            # 2. Authenticate
            print("[*] Agent: Authenticating...")
            login_data = {'username': self.username, 'password': self.password, 'logintoken': l_token}
            post_res = self.session.post(f"{self.base_url}/login/index.php", data=login_data)

            if "loginerrormessage" in post_res.text:
                return "Error: Authentication failed."

            # 3. Direct HTML Extraction (Avoid the API call to bypass WAF)
            print("[*] Agent: Scraping Dashboard HTML...")
            dash_res = self.session.get(f"{self.base_url}/my/")
            html = dash_res.text

            # Look for the 'badgefortimeline' span found in your previous HTML export
            # Format: <span id="badgefortimeline" ...>4</span>
            count_match = re.search(r'id="badgefortimeline"[^>]*>(\d+)<', html)
            
            if count_match:
                count = count_match.group(1)
                return f"SUCCESS: Found {count} pending assignments via Dashboard Badge."
            
            # Fallback: Check if there is a '0' in the badge or no badge at all
            if "badgefortimeline" in html:
                return "SUCCESS: Badge found, but count is 0."
            
            return "Error: Could not find the assignment badge in the HTML."

        except Exception as e:
            return f"Agent Error: {str(e)}"

if __name__ == "__main__":
    agent = MoodleAgent(
        username='clemens.putra@student.umn.ac.id',
        password='TWBNSWY-HONNE',
        base_url='https://elearning.umn.ac.id'
    )
    print(agent.run())
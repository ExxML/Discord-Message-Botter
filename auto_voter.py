import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import ctypes
import sys
import json
import time
import random

### TO USE THE AUTO-VOTER, YOU MUST HAVE A LIST OF TOKEN(S) in tokens.json. You cannot use account logins.
class AutoVoter():
    def __init__(self):
        try:
            with open("tokens.json", "r") as tokens_file:
                self.TOKENS = json.load(tokens_file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.TOKENS = []
        if not isinstance(self.TOKENS, list) or not all(isinstance(token, str) for token in self.TOKENS):
            input('⛔ Token Format Error ⛔\nExpected a list of strings. Example: ["token1", "token2", "token3"]')
            sys.exit()

        self.RAND_DELAY_MIN = 10  # (int) Minimum amount of MINUTES to wait between votes
        self.RAND_DELAY_MAX = 25 # (int) Maximum amount of MINUTES to wait between votes

        self.WINDOWS_VERSIONS = ["10.0", "11.0"]
        self.BROWSER_VERSIONS = [
            "114.0.5735.198", "115.0.5790.170", "115.0.5790.114", "116.0.5845.111", 
            "116.0.5845.97", "117.0.5938.149", "117.0.5938.132", "117.0.5938.62", 
            "118.0.5993.117", "118.0.5993.90", "118.0.5993.88", "119.0.6045.160", 
            "119.0.6045.123", "119.0.6045.105", "120.0.6099.224", "120.0.6099.110", 
            "120.0.6099.72", "121.0.6167.184", "121.0.6167.139", "121.0.6167.85", 
            "122.0.6261.174", "122.0.6261.128", "122.0.6261.111", "122.0.6261.95", 
            "123.0.6312.122", "123.0.6312.106", "123.0.6312.87", "123.0.6312.86", 
            "124.0.6367.207", "124.0.6367.112", "124.0.6367.91", "124.0.6367.91", 
            "125.0.6422.113", "125.0.6422.112", "125.0.6422.76", "125.0.6422.60", 
            "126.0.6478.127", "126.0.6478.93", "126.0.6478.61", "126.0.6478.57", 
            "127.0.6533.112", "127.0.6533.77"
        ]

    def load_chrome(self):
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')  # Comment for non-headless mode if needed
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        
        windows_version = random.choice(self.WINDOWS_VERSIONS)
        browser_version = random.choice(self.BROWSER_VERSIONS)
        user_agent = (
            f"Mozilla/5.0 (Windows NT {windows_version}; Win64; x64) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{browser_version} Safari/537.36 Brave/{browser_version}"  # Brave Browser - Windows 10/11 (Brave bypasses most Cloudflare detections)
        )
        options.add_argument(f'--user-agent={user_agent}')
        
        self.driver = uc.Chrome(options = options, use_subprocess = True)

        # Webdriver spoofer
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        })

        # Spoof canvas
        canvas_script = """
        const originalGetContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, ...args) {
            const ctx = originalGetContext.call(this, type, ...args);
            if (type === '2d') {
                const originalGetImageData = ctx.getImageData;
                ctx.getImageData = function(x, y, w, h) {
                    const imageData = originalGetImageData.call(this, x, y, w, h);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] = imageData.data[i] ^ 1;
                    }
                    return imageData;
                }
            }
            return ctx;
        };
        """
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": canvas_script})

    def auto_vote(self, account_idx: int):
        try:
            # Navigate to Discord login
            self.driver.get("https://discord.com/login")
            WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
            print("  Opened Discord")

            inject_token_script = f"""
                let token = "{self.shuffled_tokens[account_idx]}";
                function login(token) {{
                    setInterval(() => {{
                        document.body.appendChild(document.createElement('iframe')).contentWindow.localStorage.token = `"${{token}}"`;
                    }}, 50);
                    setTimeout(() => {{
                        location.reload();
                    }}, 2500);
                }}
                login(token);
            """
            self.driver.execute_script(inject_token_script)
            print("  Injected token")

            # Force page refresh to ensure Discord has no loading errors
            time.sleep(4)
            self.driver.execute_cdp_cmd("Network.clearBrowserCache", {})
            self.driver.refresh()

            # Wait for Discord to fully load
            WebDriverWait(self.driver, 15).until(lambda d: d.current_url == "https://discord.com/channels/@me")
            print("  Logged into Discord")
            time.sleep(1)  # Short delay to ensure Discord fully loads
            
            # Open top.gg
            self.driver.get("https://top.gg/bot/646937666251915264/vote")
            print("  Opened Top.gg")

            # Redirect to authorisation page
            login_button = WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Log')]")))
            login_button.click()
            WebDriverWait(self.driver, 15).until(lambda d: "https://discord.com/oauth2/authorize" in d.current_url)
            print("  Redirected to authorisation page")
            
            # Authorise
            self.driver.get(self.driver.current_url)
            discord_authorize_button = WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Auth')]")))
            discord_authorize_button.click()
            print("  Authorised Discord account- waiting 10s to vote...")

            # Wait 10s (watch ad to vote)
            time.sleep(10)

            if "You have already voted" in self.driver.page_source:
                print("  ℹ️ Already voted")
                return

            # Vote
            vote_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Vote')]")))
            vote_button.click()
            print("  Clicked vote button")

            # Check if voted successfully (long timeout because potential captcha)
            WebDriverWait(self.driver, 10).until(lambda d: "Thanks for voting!" in d.page_source)
            if "Thanks for voting!" in self.driver.page_source:
                print("  ✅ Voted successfully")
            else:
                print("  ❌ Unexpected result after clicking vote")
            self.driver.quit()

        except Exception as e:
            print(f"  ❌ Error with Acccount #{self.TOKENS.index(self.shuffled_tokens[account_idx]) + 1}:", e)
    
    def main(self):
        if self.TOKENS:
            self.shuffled_tokens = random.sample(self.TOKENS, len(self.TOKENS))
        else:
            input("⛔ Token Error ⛔\nNo tokens found. Please enter at least 1 token to vote with in tokens.json.")
            sys.exit()

        # Executes with tokens
        for account_idx in range(len(self.shuffled_tokens)):
            print(f"{datetime.now().strftime('%I:%M:%S %p').lstrip('0')}")
            print("Loading new undetected Chrome...")
            self.load_chrome()
            print(f"Auto-voting on Account #{self.TOKENS.index(self.shuffled_tokens[account_idx]) + 1} ({account_idx + 1}/{len(self.shuffled_tokens)})...")
            self.auto_vote(account_idx)
            print("Closing Chrome...")
            self.driver.quit()
            delay = random.uniform(self.RAND_DELAY_MIN, self.RAND_DELAY_MAX) * 60  # Random delay between votes
            print(f"Waiting {round(delay / 60)} minutes before voting again...\n")
            time.sleep(delay)

        input("✅ All accounts have been voted on. Press `Enter` to exit.")
        sys.exit()

if __name__ == "__main__":
    RELAUNCH_FLAG = "--no-relaunch"
    if RELAUNCH_FLAG not in sys.argv:
        ctypes.windll.shell32.ShellExecuteW(
            None, None, sys.executable, " ".join(sys.argv + [RELAUNCH_FLAG]), None, 1  # 0 = hidden, 1 = visible (recommended)
        )
        sys.exit()
    AutoVoter().main()
import os
import time
import random
import logging
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
LOGO = r"""
  ______ __  __ __     __     ___       __         ____     ____          
 / ___(_) /_/ // /_ __/ /    / _ |__ __/ /____    / __/__  / / /__ _    __
/ (_ / / __/ _  / // / _ \  / __ / // / __/ _ \  / _// _ \/ / / _ \ |/|/ /
\___/_/\__/_//_/\_,_/_.__/ /_/ |_\_,_/\__/\___/ /_/  \___/_/_/\___/__,__/
"""

DEFAULT_REPO_URL = "https://github.com/torvalds/linux"
DEFAULT_START_PAGE = 1
DEFAULT_SPEED_MODE = "random"

# Global variable to control the stop command
stop_thread = False


# Function to listen for the stop command
def listen_for_stop():
    global stop_thread
    while True:
        if input().strip().lower() == "stop":
            stop_thread = True
            break


def display_intro():
    """Displays the introductory information and disclaimer."""
    print("--------------------------------------------------")
    print(LOGO)
    print("GitHub Auto Follow")
    print("Made by 💜 from Zigao Wang.")
    print("This project is licensed under MIT License.")
    print("GitHub Repo: https://github.com/ZigaoWang/github-auto-follow/")
    print("--------------------------------------------------")
    print("DISCLAIMER: This script may violate GitHub's community guidelines.")
    print("Use this script for educational purposes only.")
    print("To stop the script at any time, type 'stop' in the terminal.")
    print("--------------------------------------------------")


def get_user_agreement():
    """Ensures the user reads and agrees to the disclaimer."""
    agreement = input("Type 'agree' to continue: ").strip().lower()
    if agreement != 'agree':
        print("You did not agree to the disclaimer. Exiting...")
        exit()


def load_credentials():
    """Loads GitHub credentials from environment variables."""
    load_dotenv()
    github_username = os.getenv("GITHUB_USERNAME")
    github_password = os.getenv("GITHUB_PASSWORD")
    
    if not github_username or not github_password:
        logging.warning("GitHub credentials not found in environment variables.")
        github_username = input("Enter your GitHub username: ").strip()
        github_password = input("Enter your GitHub password: ").strip()
    
    return github_username, github_password


def get_user_inputs():
    """Prompts the user for necessary inputs."""
    repo_url = input(f"Enter the GitHub repository URL (default {DEFAULT_REPO_URL}): ").strip() or DEFAULT_REPO_URL
    start_page = int(input(f"Enter the starting page (default {DEFAULT_START_PAGE}): ").strip() or DEFAULT_START_PAGE)
    speed_mode = input(
        f"Enter speed mode (fast, medium, slow, random) (default {DEFAULT_SPEED_MODE}): ").strip().lower() or DEFAULT_SPEED_MODE
    return repo_url, start_page, speed_mode


def set_delay(speed_mode):
    """Sets delay based on the chosen speed mode."""
    if speed_mode == "fast":
        return 0.1
    elif speed_mode == "medium":
        return 1
    elif speed_mode == "slow":
        return 5
    elif speed_mode == "random":
        return random.uniform(0.1, 10)
    else:
        logging.warning("Invalid speed mode. Defaulting to random.")
        return random.uniform(0.1, 10)


def github_login(driver, username, password):
    """Logs in to GitHub."""
    driver.get("https://github.com/login")
    time.sleep(2)
    driver.find_element(By.ID, "login_field").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.NAME, "commit").click()
    time.sleep(2)


def follow_stargazers(driver, repo_url, page, delay, follow_count):
    """Follows users on the stargazers page."""
    driver.get(f"{repo_url}/stargazers?page={page}")
    time.sleep(3)
    follow_buttons = driver.find_elements(By.XPATH, "//input[@type='submit' and @name='commit' and @value='Follow']")
    if not follow_buttons:
        return False, follow_count
    for button in follow_buttons:
        if stop_thread:
            break
        try:
            parent_element = button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'd-flex')]")
            username_element = parent_element.find_element(By.XPATH, ".//a[contains(@data-hovercard-type, 'user')]")
            username = username_element.get_attribute("href").split("/")[-1]
            follow_count = click_follow_button(button, delay, username, follow_count)
        except Exception as e:
            logging.error(f"Error clicking follow button: {e}")
    return True, follow_count


def click_follow_button(button, delay, username, follow_count):
    """Clicks a follow button with a delay and prints user info."""
    try:
        button.click()
        follow_count += 1
        logging.info(f"{follow_count}. Followed {username}: https://github.com/{username}")
        time.sleep(delay)
    except Exception as e:
        logging.error(f"Error clicking follow button for {username}: {e}")
    return follow_count


def create_chrome_driver():
    """Creates and returns a Chrome WebDriver instance with custom options."""
    chrome_options = Options()
    
    # Add options to avoid the "user data directory is already in use" error
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Create a unique user data directory
    temp_dir = f"/tmp/chrome_profile_{int(time.time())}"
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    
    # Additional options for headless mode if needed
    # chrome_options.add_argument("--headless")
    
    try:
        return webdriver.Chrome(options=chrome_options)
    except Exception as e:
        logging.error(f"Error creating Chrome WebDriver: {e}")
        
        # Fallback approach using Service
        try:
            service = Service()
            return webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logging.error(f"Error creating Chrome WebDriver with Service: {e}")
            raise


def main():
    """Main function to run the script."""
    global stop_thread

    display_intro()
    get_user_agreement()
    github_username, github_password = load_credentials()
    repo_url, start_page, speed_mode = get_user_inputs()
    delay = set_delay(speed_mode)

    logging.info("Starting now")

    try:
        driver = create_chrome_driver()
        github_login(driver, github_username, github_password)

        stop_listener = threading.Thread(target=listen_for_stop)
        stop_listener.daemon = True  # Make thread exit when main program exits
        stop_listener.start()

        page = start_page
        follow_count = 0

        try:
            while not stop_thread:
                followed_on_page, follow_count = follow_stargazers(driver, repo_url, page, delay, follow_count)
                if not followed_on_page:
                    logging.info(f"No follow buttons found on page {page}. Exiting.")
                    break
                page += 1
        except KeyboardInterrupt:
            logging.info("Program interrupted by user.")
        finally:
            logging.info(f"Total users followed: {follow_count}")
            driver.quit()
    
    except Exception as e:
        logging.error(f"Failed to initialize browser: {e}")
        print("\nTROUBLESHOOTING TIPS:")
        print("1. Make sure Chrome is installed on your system")
        print("2. Try installing or updating chromedriver with: 'apt-get install chromium-chromedriver'")
        print("3. If running in a headless environment, try adding 'chrome_options.add_argument(\"--headless\")'")
        print("4. Make sure no other Chrome processes are using the same profile")


if __name__ == "__main__":
    main()

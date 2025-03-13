"""
Created on December 29, 2024

This script is a web crawler designed to scrape licensee information from the Texas Medical Board website.
It uses Selenium with undetected_chromedriver to avoid detection and handles various edge cases.

Requirements:
pip install selenium undetected-chromedriver selenium seleniumbase webdriver-manager
"""
import threading
import csv
import logging
import json
import os
import time
import warnings
import colorama
from pathlib import Path
from threading import Lock
from colorama import Back, Fore, Style
import undetected_chromedriver as uc
import urllib3
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Initialize colorama for colored console output
colorama.init(autoreset=True)

# Suppress specific warnings
warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

search_init_filters_letters = [['B', 'C', 'T'], ['U', 'V', 'W'], ['X', 'Y', 'Z']]

class TexasLicenseeCrawler:
    """
    A web crawler to scrape licensee information from the Texas Medical Board website.
    """

    def __init__(self, prefix):
        """Initialize the crawler with necessary configurations."""
        self.base_url = 'https://profile.tmb.state.tx.us/Search.aspx?055e0f2c-0f98-49ff-8c47-d73f387619ec'
        self.output_file = 'results/results.csv'
        self.csv_lock = Lock()
        self.timeout = 120  # Total time to wait (in seconds)
        self.poll_interval = 2  # Time between checks (in seconds)
        self.prefix = prefix

        # Chrome options and preferences
        self.chrome_options = uc.ChromeOptions()
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-popup-blocking")
        self.chrome_options.add_argument("--ignore-certificate-errors")
        self.chrome_options.add_argument("--disable-plugins-discovery")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")

        # Search filters and configurations
        self.search_filters_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
        # self.excep_searcher = [] #this is exception searcher

        # Professional names with license type
        self.board_names_with_professional_names = {
            'Board of Medicine': [
                ('Osteopathic Physician and Surgeon', "DO"),
                ('Physician and Surgeon', "MD")
            ]
        }
        self.search_filters = []

        for board_name, professional_names_and_info in self.board_names_with_professional_names.items():
            for professional_name_and_info in professional_names_and_info:
                self.search_filters.append((board_name, professional_name_and_info))

        os.makedirs('results', exist_ok=True)

    def remove_duplicates_in_csv(self):
        """Remove duplicate rows in the CSV based on all columns."""
        with self.csv_lock:
            # Read existing data from the file
            try:
                with open(self.output_file, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    existing_data = list(reader)
            except FileNotFoundError:
                existing_data = []

            duplicate_count = 0
            # Remove duplicates based on all columns
            seen_rows = set()
            unique_data = []
            for row in existing_data:
                # Create a tuple of all values in the row to track duplicates
                row_tuple = tuple(row.items())  # Hashable representation of the row
                if row_tuple not in seen_rows:
                    seen_rows.add(row_tuple)
                    unique_data.append(row)
                else:
                    duplicate_count += 1

            logger.info(f"Duplicates found: {duplicate_count}")

            # Write the unique data back to the CSV
            if existing_data:  # Ensure there is data to infer fieldnames
                fieldnames = existing_data[0].keys()
            else:
                fieldnames = []

            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(unique_data)

    def write_excep_searcher(self, data, mode='w'):
        """
        Writes or appends data to a JSON file.
        
        :param file_path: Path to the JSON file.
        :param data: Data to write (must be a dictionary or list).
        :param mode: 'w' to overwrite, 'a' to append (default is 'w').
        """
        file_path = 'excep/searcher.json'
        try:
            if mode == 'a' and os.path.exists(file_path):
                # Read existing data if appending
                with open(file_path, 'r') as file:
                    existing_data = json.load(file)
                if isinstance(existing_data, list):
                    existing_data.append(data)  # Append to list
                else:
                    existing_data = [existing_data, data]  # Convert to list and append
                data = existing_data

            # Write data to file with indentation
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)
            # print(f"Data written to {file_path} successfully.")
        except Exception as e:
            print(f"Error writing to JSON file: {e}")

    def read_excep_searcher(self):
        """
        Reads data from a JSON file.
        
        :param file_path: Path to the JSON file.
        :return: Data from the JSON file (dictionary or list).
        """

        file_path = 'excep/searcher.json'
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            return data
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            return None
        


    def extra(self, text):
        """Check if the text contains any of the exceptions."""
        excep_searcher = self.read_excep_searcher()
        return any(t in text for t in excep_searcher)

    def waited_for_windows_load(self, ch_driver, time_out=100):
        """Wait for the driver to load the window."""
        try:
            WebDriverWait(ch_driver, time_out).until(
                lambda ch_driver: ch_driver.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            logger.error("Page load timed out.")
            return False

    def generateAddLetterPrefixes(self, prefix):
        """Generate two-letter prefixes based on a given prefix."""
        return [prefix + letter for letter in self.search_filters_letters]

    def save_to_csv(self, results):
        """Save results to CSV in a thread-safe manner."""
        with self.csv_lock:
            with open(self.output_file, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = ["Full_Name", "License_Type", "License_Number", "Status", "Professional", "Issued", "Expired"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                for result in results:
                    writer.writerow(result)

    def dataInput(self, name, license, status, professional, issuance_date, expiration_date):
        """Prepare and save data to CSV."""
        fields = {
            "Full_Name": name.text.replace(' ', '').split(',')[0],
            "License_Type": name.text.replace(' ', '').split(',')[1],
            "License_Number": license.text,
            "Issued": issuance_date.text,
            "Expired": expiration_date.text,
            "Status": status.text,
            "Professional": professional.text
        }
        if fields:
            self.save_to_csv([fields])

    def scraping_get_data(self, prefix, depth):
        """Scrape and save data from the current page."""
        name = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[2]/div[2]/div[1]/table/tbody/tr[1]/td/label[2]')))
        license = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[2]/div[2]/div[1]/table/tbody/tr[2]/td/label[2]')))
        status = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[2]/div[2]/div[1]/table/tbody/tr[4]/td/label[2]')))
        professional = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[2]/div[2]/div[1]/div[2]/div[2]/div/table/tbody/tr[3]/td/label[3]')))
        issuance_date = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[2]/div[2]/div[1]/div[2]/div[2]/div/table/tbody/tr[4]/td/label[2]')))
        expiration_date = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[2]/div[2]/div[1]/div[2]/div[2]/div/table/tbody/tr[5]/td/label[2]')))
        self.dataInput(name, license, status, professional, issuance_date, expiration_date)
        print(f"{'' if depth == 0 else f'|{'    '*(depth)}Ͱ---'}{Fore.LIGHTGREEN_EX}name: {name.text}{Fore.RESET}, {Fore.LIGHTGREEN_EX}\tlicense: {license.text}{Fore.RESET}, {Fore.LIGHTGREEN_EX}\tstatus: {status.text}{Fore.RESET}, {Fore.LIGHTGREEN_EX}\tprofessional: {professional.text}{Fore.RESET}, {Fore.LIGHTGREEN_EX}\tissuance: {issuance_date.text}{Fore.RESET}, {Fore.LIGHTGREEN_EX}\texpiration: {expiration_date.text}{Fore.RESET}" )
        homebutton = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[2]/div[1]/div[1]/ul/li[2]/a')))
        homebutton.click()
        time.sleep(2)

    def searchList(self, prefix):
        try:
            """Search for licensees based on a prefix."""
            self.driver.get(self.base_url)
            self.waited_for_windows_load(self.driver)
            board_input_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='ctl00$BodyContent$tbFirstName']")))
            board_input_element.clear()
            board_input_element.send_keys(prefix)
            time.sleep(2)

            license_type_input_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//select[@name='ctl00$BodyContent$ddLicenseType']")))
            license_type_input_element.send_keys('Physician')
            self.waited_for_windows_load(self.driver)
            time.sleep(2)

            license_submit_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='ctl00$BodyContent$btnSearch']")))
            license_submit_button.click()
            self.waited_for_windows_load(self.driver)
            time.sleep(2)
            contacts_list = []
        
            contacts_list = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr td a'))
            )
            if not contacts_list:
                print(f"------------------------------------------------------------------------------------------------------------------------------------------{Fore.RED}No contacts found.")
        except TimeoutException:
            contacts_list = []  # Return an empty list instead of failing
        except Exception as e:
            print(f"-------------------------------------------------------------------------------------------------------------------------------------------{Back.RED}{Fore.BLACK}Unexpected error: {e}")
            contacts_list = []  # Return an empty list instead of failing
        
        return contacts_list

    def advancedPrefixSearch(self, prefixs, depth=0):
        """Perform an advanced search using prefixes."""
        for prefix in prefixs:
            if self.extra(prefix):
                continue
            userlists = self.searchList(prefix)
            if len(userlists) == 0:
                print(f"{Fore.YELLOW + prefix +Fore.RESET if depth == 0 else f"Ͱ----{Fore.YELLOW + prefix +Fore.RESET}" if depth == 1 else f'|{'    '*(depth-1)}└---{Fore.YELLOW + prefix +Fore.RESET}'} : {Back.LIGHTRED_EX + Fore.BLACK}EMPTY" )
                self.write_excep_searcher(prefix, mode='a')
                # self.excep_searcher.append(prefix)
                continue
            if len(userlists) < 50:
                print(f"{Fore.YELLOW + prefix +Fore.RESET if depth == 0 else f"Ͱ----{Fore.YELLOW + prefix +Fore.RESET}" if depth == 1 else f'|{'    '*(depth-1)}└---{Fore.YELLOW + prefix +Fore.RESET}'} : {Back.LIGHTBLUE_EX + Fore.LIGHTRED_EX} {len(userlists)} " )
                # self.excep_searcher.append(prefix)
                self.write_excep_searcher(prefix, mode='a')
                for user in userlists:
                    try:
                        if user is None:
                            print(f"---------------------------------------------------------------{Back.LIGHTYELLOW_EX}Warning: Found a None element in userlists.")
                            continue
                        
                        user_text = user.text.strip()
                        if not user_text:
                            print(f"---------------------------------------------------------------{Back.LIGHTYELLOW_EX}Warning: User element has no text.")
                            continue
                        
                        self.driver.execute_script("arguments[0].scrollIntoView();", user)
                        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(user))
                        user.click()
                        
                        self.waited_for_windows_load(self.driver)
                        self.scraping_get_data(prefix, depth)
                    
                    except StaleElementReferenceException:
                        print(f"--------------------------------------------------------------{Back.LIGHTRED_EX}Error: StaleElementReferenceException - Retrying search.")
                    except ElementClickInterceptedException:
                        print(f"--------------------------------------------------------------{Back.LIGHTRED_EX}Error: ElementClickInterceptedException - Could not click the element.")
                        self.driver.execute_script("arguments[0].click();", user)
                    except NoSuchElementException:
                        print(f"--------------------------------------------------------------{Back.LIGHTRED_EX}Error: NoSuchElementException - Element not found.")
                    except TimeoutException:
                        print(f"--------------------------------------------------------------{Back.LIGHTRED_EX}Error: TimeoutException - Page did not load in time.")
                    except Exception as e:
                        print(f"--------------------------------------------------------------{Back.RED}Unexpected error: {Back.RESET}{Fore.CYAN}{e}")
                continue
            else:
                print(f"{Fore.YELLOW + prefix +Fore.RESET if depth == 0 else f"Ͱ----{Fore.YELLOW + prefix +Fore.RESET}" if depth == 1 else f'|{'    '*(depth-1)}└---{Fore.YELLOW + prefix +Fore.RESET}'} : {Back.LIGHTMAGENTA_EX + Fore.LIGHTCYAN_EX}MANY")
            addLetterPrefixes = self.generateAddLetterPrefixes(prefix)
            self.advancedPrefixSearch(addLetterPrefixes, depth + 1)

    def run(self):
        """Run the crawler."""
        path = ChromeDriverManager().install()
        self.driver = uc.Chrome(options=self.chrome_options, headless=True, driver_executable_path=path)

        # Write CSV headers
        with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["Full_Name", "License_Type", "License_Number", "Status", "Professional", "Issued", "Expired"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

        print(f"{Back.LIGHTCYAN_EX + Fore.LIGHTYELLOW_EX}+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-  {Back.RESET + Fore.LIGHTCYAN_EX}START{Back.LIGHTCYAN_EX + Fore.LIGHTYELLOW_EX}  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-")
        self.advancedPrefixSearch(self.prefix)

        try:
            self.driver.close()
        except:
            pass
        logger.info("Completed")
        self.remove_duplicates_in_csv()

def main():
    # Create 5 bots and run them concurrently using threading
    bots = [TexasLicenseeCrawler(prefix) for prefix in search_init_filters_letters]
    threads = []

    for bot in bots:
        thread = threading.Thread(target=bot.run)
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

if __name__ == '__main__':
    # crawler = TexasLicenseeCrawler('A')
    # crawler.run()
    main()

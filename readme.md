# Medical Scraping Selenium

This project is designed to scrape medical data using Selenium.

## Prerequisites

- Python 3.x
- Selenium
- WebDriver for your browser (e.g., ChromeDriver for Chrome)

## Installation

1. Clone the repository:
    ```bash
    git clone hhttps://github.com/Rieznichenko/Texas_scraper.git
    ```
2. Navigate to the project directory:
    ```bash
    cd Medical-Scraping-Selenium
    ```
3. Install the required packages:
    ```bash
    pip install undetected_chromedriver selenium seleniumbase webdriver_manager pandas flask flask_socketio colorama
    ```

## Usage

1. Update the `scraper.py` file with the necessary configurations.
2. Run the scraper:
    ```bash
    python scraper.py 
    ```
    or
    ```bash
    nohup python3 scraper.py > logs/output.log 2>&1 & # if install in remote PC
    ```
3. Run server:
    ```bash
    python server.py
    ```
    or
    ```bash
    nohup python3 server.py > logs/flask_output.log 2>&1 & # if install in remote PC
    ```



## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

## License

This project is none licensed, You can use all for free.

## Contact

For any questions or suggestions, please open an issue or comment.

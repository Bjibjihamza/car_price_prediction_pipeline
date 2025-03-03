from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
from datetime import datetime
import os
import requests
import re
import pandas as pd

def scrape_car_listing(url, driver, wait):
    """Scrape data from a single car listing URL"""
    driver.get(url)
    
    # Initialize a dictionary to store the extracted data
    data = {}
    
    # Scrape title (car name)
    try:
        car_name_section = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.car-name')))
        data['Titre'] = car_name_section.text.strip()
        
        # Create a sanitized version of car name for the folder (remove spaces and special characters)
        sanitized_car_name = re.sub(r'[^\w\-_]', '_', data['Titre'])
        folder_path = os.path.join('../data/auto24', sanitized_car_name)
        
        # Create the folder structure if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
    except Exception as e:
        print(f"Error scraping car name: {e}")
        data['Titre'] = "Unknown"
        folder_path = os.path.join('../data/auto24', f"car_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        os.makedirs(folder_path, exist_ok=True)
    
    # Scrape price
    try:
        price_section = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h4.new-price')))
        data['Prix'] = price_section.text.strip()
    except Exception as e:
        print(f"Error scraping price: {e}")
        data['Prix'] = ""
    
    # Add a unique ID based on the current timestamp
    data['ID'] = datetime.now().strftime('%Y%m%d%H%M%S')
    
    # Scrape images
    try:
        # Find all image elements in the swiper-slide containers
        image_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.carousel-image img')))
        
        # Extract image URLs
        image_urls = []
        for i, img in enumerate(image_elements):
            image_url = img.get_attribute('src')
            if image_url:
                image_urls.append(image_url)
                
        # Download the images
        print(f"Found {len(image_urls)} images. Starting download...")
        
        for i, img_url in enumerate(image_urls):
            try:
                # Get high-quality image by replacing 'medium' with original
                high_quality_url = img_url.replace('/medium/', '/')
                
                # Create filename for the image
                file_ext = os.path.splitext(high_quality_url.split('/')[-1])[1]
                if not file_ext:
                    file_ext = '.jpg'  # Default extension if none is found
                    
                file_name = f"image_{i+1:02d}{file_ext}"
                file_path = os.path.join(folder_path, file_name)
                
                # Download the image
                response = requests.get(high_quality_url)
                if response.status_code == 200:
                    with open(file_path, 'wb') as file:
                        file.write(response.content)
                    print(f"Downloaded image {i+1}/{len(image_urls)}: {file_name}")
                else:
                    print(f"Failed to download image {i+1}: HTTP status {response.status_code}")
                    
            except Exception as e:
                print(f"Error downloading image {i+1}: {e}")
        
        # Store the folder path containing images
        data['Images_téléchargées'] = folder_path
        
    except Exception as e:
        print(f"Error scraping images: {e}")
        data['Images_téléchargées'] = ""
    
    # Scrape additional information from the car overview section
    try:
        # Find all overview items
        overview_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.overview-item')))
    
        # Process each overview item
        for item in overview_items:
            # Get the title and value for each item
            try:
                title_element = item.find_element(By.CSS_SELECTOR, 'h3.overview-title')
                value_element = item.find_element(By.CSS_SELECTOR, 'p.overview-value')
                
                title = title_element.text.strip()
                value = value_element.text.strip()
                
                # Map the titles to our CSV field names
                if "Date de mise en circulation" in title:
                    data['Année'] = value
                elif "Kilométrage" in title:
                    data['Kilométrage'] = value
                elif "Type de carburant" in title:
                    data['Carburant'] = value
                elif "Boite de vitesse" in title:
                    data['Transmission'] = value
                elif "Places" in title:
                    data['Places'] = value
            except Exception as e:
                print(f"Error extracting overview data: {e}")
    except Exception as e:
        print(f"Error processing overview section: {e}")
    
    # Scrape the options/features section
    try:
        # Find all feature titles
        feature_titles = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'h3.feature-title')))
        
        # Extract the text from each feature title
        features = []
        for feature in feature_titles:
            features.append(feature.text.strip())
        
        # Join all features with commas for CSV storage
        data['Options'] = ', '.join(features)
    except Exception as e:
        print(f"Error processing features section: {e}")
        data['Options'] = ""
    
    # Scrape only the Puissance fiscale and Condition from the summary section
    try:
        # Find all summary cards
        summary_cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.summary-card')))
        
        # Process each summary card
        for card in summary_cards:
            try:
                # Get the title and value from each card
                title_element = card.find_element(By.CSS_SELECTOR, 'h3.summary-title')
                value_element = card.find_element(By.CSS_SELECTOR, 'div.summary-value')
                
                title = title_element.text.strip()
                # Clean up the value (remove any non-breaking spaces and photo preview text)
                value = value_element.text.strip().split('  ')[0].strip()
                
                # Only extract Puissance fiscale and Condition
                if "Puissance fiscale" in title:
                    data['Puissance_fiscale'] = value
                elif "Condition" in title:
                    data['Condition'] = value
            except Exception as e:
                print(f"Error extracting summary card data: {e}")
    except Exception as e:
        print(f"Error processing summary section: {e}")
    
    # Store the URL
    data['URL_annonce'] = url
    
    return data

def main():
    # Path to the CSV file with the URLs
    input_csv_path = '../data/auto24/auto24_listings.csv'
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # Create a WebDriverWait instance
    wait = WebDriverWait(driver, 10)
    
    # Read the CSV file with the URLs
    try:
        # Check if the file uses semicolon as delimiter
        with open(input_csv_path, 'r', encoding='utf-8') as file:
            first_line = file.readline()
            if ';' in first_line:
                delimiter = ';'
            else:
                delimiter = ','
                
        # Read the CSV into a pandas DataFrame
        df = pd.read_csv(input_csv_path, delimiter=delimiter)
        
        # Check if 'URL de l'annonce' column exists
        if 'URL de l\'annonce' in df.columns:
            url_column = 'URL de l\'annonce'
        elif 'URL' in df.columns:
            url_column = 'URL'
        else:
            # Try to find a column that might contain URLs
            for col in df.columns:
                if df[col].astype(str).str.contains('http').any():
                    url_column = col
                    break
            else:
                raise ValueError("Could not find a column containing URLs")
                
        print(f"Using URL column: {url_column}")
        
        # Get the list of URLs to scrape
        urls = df[url_column].tolist()
        print(f"Found {len(urls)} URLs to scrape")
        
        # Define output CSV file
        output_csv_path = '../data/auto24/scraped_car_data_full.csv'
        
        # Define all the field names we want to include in the CSV
        fieldnames = [
            'ID', 'Titre', 'Prix', 'Année', 'Kilométrage', 'Carburant', 'Transmission', 'Places',
            'Puissance_fiscale', 'Condition', 'Options', 'Images_téléchargées', 'URL_annonce'
        ]
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
        
        # Check if the output CSV file exists
        file_exists = os.path.isfile(output_csv_path)
        
        # Open the output CSV file
        with open(output_csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header only if the file doesn't exist
            if not file_exists:
                writer.writeheader()
            
            # Process each URL
            for index, url in enumerate(urls):
                print(f"Processing URL {index+1}/{len(urls)}: {url}")
                
                try:
                    # Scrape data from the URL
                    data = scrape_car_listing(url, driver, wait)
                    
                    # Write the data to the CSV file
                    writer.writerow(data)
                    
                    print(f"Successfully scraped data for: {data.get('Titre', 'Unknown')}")
                    
                    # Add a small delay between requests to be nice to the server
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Error processing URL {url}: {e}")
                    continue
        
        print(f"All URLs processed. Data saved to {output_csv_path}")
        
    except Exception as e:
        print(f"Error reading input CSV file: {e}")
    
    finally:
        # Close the browser
        driver.quit()

if __name__ == "__main__":
    main()
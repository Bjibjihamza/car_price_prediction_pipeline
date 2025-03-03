import time
import csv
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re



def setup_driver():
    """Configure et initialise le driver Selenium."""
    options = Options()
    options.add_argument("--headless")  # Exécuter sans interface graphique
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")  # Réduire les logs inutiles

    # Utiliser ChromeDriverManager pour télécharger et gérer le driver
    service = Service(ChromeDriverManager().install())  # This will handle the driver installation automatically

    driver = webdriver.Chrome(service=service, options=options)
    return driver

def scrape_wandaloo() :

    for i in range(2,3) :
        url = f'https://www.wandaloo.com/occasion/?marque=0&modele=0&budget=0&categorie=0&moteur=0&transmission=0&equipement=-&ville=0&vendeur=0&abonne=0&za&pg={i}'

        driver = setup_driver()
        driver.get(url)

        # Wait for the page to load completely (change the class or element based on what loads last)
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'odd')))
        except Exception as e:
            print(f"❌ Timeout: Impossible de charger la page ({e})")
            driver.quit()
            return
        
        data = []
        
        try:
            listings = driver.find_elements(By.CSS_SELECTOR, 'li.odd, li.even')

            if not listings:
                print("❌ Aucune annonce trouvée ! Vérifie si le site a changé.")
                return

            print(f"✅ {len(listings)} annonces trouvées !")

            # **Parcourir les annonces**
            for idx, listing in enumerate(listings, start=1) :
                try:
                    # **Titre**
                    titre = listing.find_element(By.CSS_SELECTOR, 'p.titre').text.strip() if listing.find_elements(By.CSS_SELECTOR, 'p.titre') else "N/A"

                    # **Prix**
                    prix = listing.find_element(By.CSS_SELECTOR, 'p.prix').text.strip().replace('DH', '').strip() + " DH" if listing.find_element(By.CSS_SELECTOR, 'p.prix').text.strip().replace('DH', '').strip() + " DH" else "Prix non spécifié"

                    # **Date de publication**
                    date_pub = listing.find_element(By.CSS_SELECTOR, 'span.dateHeure').text.strip() if listing.find_element(By.CSS_SELECTOR, 'span.dateHeure') else "N/A"


                    # **Ville** 
                    ville = listing.find_element(By.CSS_SELECTOR, 'span.city').text.strip() if listing.find_element(By.CSS_SELECTOR, 'span.city') else "N/A"

                    #**URL de l'anonce **
                    annonce_url = listing.find_element(By.CSS_SELECTOR, 'a.btn.orange-blanc.medium').get_attribute('href') if listing.find_element(By.CSS_SELECTOR, 'a.btn.orange-blanc.medium') else "N/A"

                    # **URL de l'image**
                    image_url = listing.find_element(By.CSS_SELECTOR, 'a.img img').get_attribute('src') if listing.find_element(By.CSS_SELECTOR, 'a.img img') else "N/A"

                    # ** More details **
                    details = listing.find_elements(By.CSS_SELECTOR, 'ul.detail li')
                    carburant = details[0].text.strip() if len(details) > 0 else "N/A"
                    annee = details[1].text.strip() if len(details) > 1 else "N/A"

                    # **Transmission**
                    #transmission = listing.find_element(By.XPATH, ".//span[contains(text(),'Automatique') or contains(text(),'Manuelle')]").text.strip() if listing.find_elements(By.XPATH, ".//span[contains(text(),'Automatique') or contains(text(),'Manuelle')]") else "N/A"

                    # **Créateur** :
                    createur = 'Particulier' if 'Pro.' not in listing.text else 'Pro'


                    # **Sauvegarde des données**
                    data.append([idx, titre, prix, date_pub, annee, carburant,  createur, ville, annonce_url, image_url])

                except Exception as e:
                    print(f"⚠️ Erreur avec l'annonce {idx}: {e}")

        except Exception as e:
            print(f"❌ Erreur lors de l'extraction: {e}")


        driver.quit()
    save_to_csv(data)





def save_to_csv(data):
    """Sauvegarde les données dans un fichier CSV."""
    output_folder = "../data/wandaloo"
    os.makedirs(output_folder, exist_ok=True)
    output_file = os.path.join(output_folder, "wandaloo_listings.csv")

    with open(output_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["ID", "Titre", "Prix", "Date de publication", "Année", "Type de carburant", "Créateur", "Ville", "URL de l'annonce", "Image URL"])
        writer.writerows(data)

    print(f"✅ Données sauvegardées dans {output_file}")



scrape_wandaloo() 

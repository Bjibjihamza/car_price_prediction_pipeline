import os
import re
import csv
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from tenacity import retry, stop_after_attempt, wait_fixed

def main():
    """Fonction principale pour exécuter le scraper de base."""
    print("🚗 Démarrage du scraper Auto24.ma (Partie 1: Liens)...")
    
    # Scraping des annonces de base
    print("\n📋 Scraping des annonces principales...")
    try:
        basic_data = scrape_auto24(max_scrolls=5)
    except Exception as e:
        print(f"❌ Erreur critique lors du scraping : {str(e)[:100]}")
        return

    if not basic_data or len(basic_data) == 0:
        print("❌ Aucune donnée trouvée. Arrêt du programme.")
        return
    
    # Sauvegarde des annonces de base
    basic_csv = save_to_csv(basic_data, "auto24_listings.csv")
    
    print("\n✅ SCRAPING DE BASE TERMINÉ AVEC SUCCÈS !")
    print(f"Annonces de base : {basic_csv}")
    print(f"Utilisez maintenant details_scraper.py pour obtenir les détails complets.")

def init_auto24_driver(headless=True):
    options = Options()
    
    # Configuration anti-détection avancée
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Paramètres de performance
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    
    # User-Agent aléatoire
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")

    # Désactiver les logs inutiles
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    service = Service(ChromeDriverManager().install())

    
    driver = webdriver.Chrome(service=service, options=options)
    
    # Masquer les traces WebDriver
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        }
    )
    
    return driver

def create_folder_name(title, idx):
    """Crée un nom de dossier valide pour stocker les images d'une annonce."""
    folder_name = re.sub(r'[^\w\s-]', '', title)
    folder_name = re.sub(r'\s+', '_', folder_name)[:50]
    return f"{idx}_{folder_name}"

def extract_feature(features, index, is_mileage=False):
    """Extrait une caractéristique spécifique"""
    try:
        if len(features) > index:
            text = features[index].text.strip()
            return text.split('\n')[-1].replace('RW', '').strip() if is_mileage else text.split('\n')[-1].strip()
        return "N/A"
    except:
        return "N/A"

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def extract_text_safe(parent, selector):
    """Extrait le texte d'un élément en toute sécurité"""
    try:
        element = WebDriverWait(parent, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
        return element.text.strip()
    except:
        return "N/A"

def scrape_auto24(max_scrolls=5):
    """Scrape les annonces de voitures sur Auto24.ma avec chargement infini"""
    driver = init_auto24_driver()
    data = []
    listing_id_counter = 1

    try:
        driver.get("https://auto24.ma/buy-cars?isNewCar=false")
        
        # Logique de scroll améliorée
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        
        while scroll_attempts < max_scrolls:
            driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8)")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1

        listings = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card-holder")))
        
        print(f"✅ {len(listings)} annonces trouvées au total")

        for idx in range(len(listings)):
            try:
                # Re-fetch listings après chaque retour
                listings = driver.find_elements(By.CSS_SELECTOR, "div.card-holder")
                listing = listings[idx]

                # Scroll pour activer le lien
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", listing)
                time.sleep(0.5)

                # Extraction du lien par clic
                actions = ActionChains(driver)
                actions.move_to_element(listing).perform()
                time.sleep(1)
                listing.click()
                time.sleep(2)
                link = driver.current_url
                driver.back()
                time.sleep(3)

                # Rechargement des éléments après retour
                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card-holder")))
                listings = driver.find_elements(By.CSS_SELECTOR, "div.card-holder")
                listing = listings[idx]

                # Extraction des autres détails
                title = extract_text_safe(listing, "span.card-model")
                price = extract_text_safe(listing, "span.card-price")
                
                features = listing.find_elements(By.CSS_SELECTOR, "div.card-features > span.features-container")
                transmission = extract_feature(features, 0)
                fuel_type = extract_feature(features, 1)
                mileage = extract_feature(features, 2, True)
                
                seller_type = "Professionnel" if listing.find_elements(By.CSS_SELECTOR, "div.card-brand-logo") else "Particulier"
                
                folder_name = create_folder_name(title, listing_id_counter)
                
                data.append([
                    listing_id_counter,
                    title,
                    _clean_price(price),
                    transmission,
                    fuel_type,
                    mileage,
                    seller_type,
                    link,
                    folder_name
                ])
                
                listing_id_counter += 1
                print(f"✔ Annonce {listing_id_counter - 1} traitée")

            except StaleElementReferenceException:
                print(f"⚠️ Élément périmé, rechargement de la liste...")
                continue
            except Exception as e:
                print(f"⚠️ Erreur annonce {listing_id_counter}: {str(e)[:50]}...")
                continue

    except Exception as e:
        print(f"❌ Erreur critique : {str(e)[:50]}...")
    finally:
        driver.quit()
    
    return data

def _clean_price(price_str):
    """Nettoyage du prix"""
    try:
        return int(price_str.replace('DH', '').replace(' ', '').replace('\u202f', '').strip())
    except:
        return 0

def save_to_csv(data, filename):
    """Sauvegarde les données dans un fichier CSV."""
    output_folder = "../data/auto24"
    os.makedirs(output_folder, exist_ok=True)
    output_file = os.path.join(output_folder, filename)

    with open(output_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow([
            "ID", "Titre", "Prix", "Transmission", "Type de carburant", 
            "Kilométrage", "Créateur", "URL de l'annonce", "Dossier d'images"
        ])
        writer.writerows(data)

    print(f"✅ Données sauvegardées dans {output_file}")
    return output_file

if __name__ == "__main__":
    main()
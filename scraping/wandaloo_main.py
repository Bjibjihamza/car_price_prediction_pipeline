import time
import csv
import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

# Configuration de Selenium
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Définir les chemins des fichiers
input_csv_path = '../data/wandaloo/wandaloo_listings.csv'
output_csv_path = '../data/wandaloo/wandaloo_data.csv'

# Créer le dossier de sortie s'il n'existe pas
os.makedirs('../data/wandaloo', exist_ok=True)

# Lire le fichier CSV contenant les liens
df = pd.read_csv(input_csv_path)

# Initialiser une liste pour stocker les données de toutes les voitures
all_cars_data = []

# Fonction pour révéler toutes les sections d'options
def reveal_all_option_sections():
    try:
        # Trouver tous les boutons "Afficher"
        show_buttons = driver.find_elements(By.XPATH, "//p[contains(@class, 'head accordion')]//button[contains(@class, 'pull-right')]")
        
        # Cliquer sur chaque bouton pour révéler les options
        for button in show_buttons:
            try:
                # Vérifier si le panneau est déjà visible
                parent_header = button.find_element(By.XPATH, "./..")
                section_id = parent_header.get_attribute("id") if parent_header.get_attribute("id") else "unknown"
                
                # Essayer de trouver le panneau associé
                panel = parent_header.find_element(By.XPATH, "./following-sibling::ul[contains(@class, 'params')]")
                
                # Si le panneau est caché (style="display: none;"), cliquer sur le bouton
                if panel.get_attribute("style") and "none" in panel.get_attribute("style"):
                    print(f"Clicking to show section: {section_id}")
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.5)  # Attendre que l'animation se termine
                else:
                    print(f"Section already visible: {section_id}")
                    
            except Exception as e:
                print(f"Erreur lors du clic sur un bouton: {str(e)[:150]}")
                continue
        
        # Attendre que tous les panneaux soient visibles
        time.sleep(1)
        
    except Exception as e:
        print(f"Erreur lors de l'affichage des sections d'options: {str(e)[:150]}")

# Fonction pour extraire les options disponibles d'une section
def extract_options_from_section(section_title):
    options_list = []
    try:
        # Trouver la section par son titre
        section = driver.find_element(By.XPATH, f"//p[contains(@class, 'head') and contains(text(), '{section_title}')]")
        
        # Remonter à l'élément parent div.cell
        section_div = section.find_element(By.XPATH, "./ancestor::div[contains(@class, 'cell')]")
        
        # Trouver toutes les options dans cette section
        options_elements = section_div.find_elements(By.XPATH, ".//ul[contains(@class, 'params')]/li")
        
        for element in options_elements:
            try:
                param_elem = element.find_element(By.XPATH, ".//p[@class='param']")
                option_name = param_elem.text
                
                # Vérifier si l'option est disponible (image oui.png)
                value_elem = element.find_element(By.XPATH, ".//p[@class='value']")
                
                # Vérifier si la valeur contient une image
                img_elems = value_elem.find_elements(By.XPATH, "./img")
                
                if img_elems and "oui.png" in img_elems[0].get_attribute("src"):
                    options_list.append(option_name)
                # Pour les options qui ont une valeur textuelle (comme "Sellerie: Cuir / Tissu")
                elif not img_elems and value_elem.text.strip() and value_elem.text.strip() != "-":
                    options_list.append(f"{option_name}: {value_elem.text.strip()}")
                    
            except Exception as e:
                print(f"Erreur lors de l'extraction d'une option: {str(e)[:150]}")
                continue
    except Exception as e:
        print(f"Erreur lors de l'extraction des options de la section '{section_title}': {str(e)[:150]}")
    
    return options_list

# Boucler sur chaque ligne du CSV pour traiter chaque URL
for index, row in df.iterrows():
    try:
        print(f"Traitement de l'annonce {index+1}/{len(df)}: {row['Titre']}")
        
        # Extraire les informations du CSV
        car_id = row['ID']
        titre = row['Titre']
        prix = row['Prix']
        date_publication = row['Date de publication']
        url = row['URL de l\'annonce']
        
        # Accéder à l'URL
        driver.get(url)
        
        # Attendre que la page soit chargée
        time.sleep(5)
        
        # Dictionnaire pour stocker les informations
        infos = {}
        
        # Ajouter les informations dans l'ordre souhaité
        infos['ID'] = car_id
        infos['Titre'] = titre
        infos['Prix'] = prix
        infos['Date de publication'] = date_publication
        
        try:
            # Scraper les données précédentes comme le modèle, ville, etc.
            model = driver.find_element(By.XPATH, "//ul[@class='icons clearfix']/li[1]//p[@class='tag']").text
            city = driver.find_element(By.XPATH, "//ul[@class='icons clearfix']/li[2]//p[@class='tag']").text
            seller = driver.find_element(By.XPATH, "//ul[@class='icons clearfix']/li[3]//p[@class='tag']").text
            condition = driver.find_element(By.XPATH, "//ul[@class='icons clearfix']/li[4]//p[@class='tag']").text
            mileage = driver.find_element(By.XPATH, "//ul[@class='icons clearfix']/li[5]//p[@class='tag']").text
            fuel = driver.find_element(By.XPATH, "//ul[@class='icons clearfix']/li[6]//p[@class='tag']").text
            transmission = driver.find_element(By.XPATH, "//ul[@class='icons clearfix']/li[7]//p[@class='tag']").text

            # Scraper les informations supplémentaires
            year = driver.find_element(By.XPATH, "//ul[@class='params my-panel']/li[1]//p[@class='value']").text
            first_owner_img = driver.find_element(By.XPATH, "//ul[@class='params my-panel']/li[2]//p[@class='value']/img").get_attribute("src")
            customs = driver.find_element(By.XPATH, "//ul[@class='params my-panel']/li[3]//p[@class='value']/img").get_attribute("src")
            engine_type = driver.find_element(By.XPATH, "//ul[@class='params my-panel']/li[4]//p[@class='value']").text
            tax_power = driver.find_element(By.XPATH, "//ul[@class='params my-panel']/li[5]//p[@class='value']").text
            dynamic_power = driver.find_element(By.XPATH, "//ul[@class='params my-panel']/li[6]//p[@class='value']").text
            color = driver.find_element(By.XPATH, "//ul[@class='params my-panel']/li[7]//p[@class='value']").text
            vehicle_condition = driver.find_element(By.XPATH, "//ul[@class='params my-panel']/li[8]//p[@class='value']").text

            # Vérifier si le véhicule est dédouané et s'il s'agit de la 1ère main
            first_owner = "Oui" if "non.png" not in first_owner_img else "Non"
            customs_status = "Dédouanée" if "oui.png" in customs else "Non dédouanée"

            # Ajouter aux informations selon l'ordre souhaité
            infos['Année'] = year
            infos['Type de carburant'] = fuel
            infos['Transmission'] = transmission
            infos['Créateur'] = seller
            infos['Type de véhicule'] = 'Voitures d\'occasion, à vendre'  # Valeur par défaut
            infos['Secteur'] = city
            infos['Kilométrage'] = mileage
            
            # Extraire la marque et le modèle
            marque = model.split()[0] if ' ' in model else model
            modele = ' '.join(model.split()[1:]) if ' ' in model else ''
            infos['Marque'] = marque
            infos['Modèle'] = modele
            
            infos['Nombre de portes'] = '5'  # Valeur par défaut
            infos['Origine'] = 'WW au Maroc'  # Valeur par défaut
            infos['Première main'] = condition  # Utiliser condition comme "Première main"
            infos['Puissance fiscale'] = tax_power
            infos['État'] = vehicle_condition

            # Révéler toutes les sections d'options avant d'extraire les données
            reveal_all_option_sections()

            # Extraire les options de chaque section
            securite_options = extract_options_from_section("Sécurité")
            confort_options = extract_options_from_section("Confort")
            esthetique_options = extract_options_from_section("Esthétique")

            # Fusionner toutes les options dans une seule colonne
            all_options = []
            if securite_options:
                all_options.append("Sécurité: " + ", ".join(securite_options))
            if confort_options:
                all_options.append("Confort: " + ", ".join(confort_options))
            if esthetique_options:
                all_options.append("Esthétique: " + ", ".join(esthetique_options))

            infos['Équipements'] = " | ".join(all_options) if all_options else "Aucune option"
            infos['Ville du vendeur'] = city
            
            # Créer un nom de dossier pour la voiture
            car_id_from_url = url.split('/')[-1].split('.')[0]  # Extrait l'ID de la voiture à partir de l'URL
            folder_name = f"{car_id}_{marque.lower()}_{modele.lower().replace(' ', '_')}"
            folder_path = os.path.join("../data/wandaloo", folder_name)

            # Créer le dossier s'il n'existe pas
            os.makedirs(folder_path, exist_ok=True)

            # Ajouter le nom du dossier aux informations
            infos['Dossier d\'images'] = folder_name

            # Télécharger les images
            try:
                # Trouver toutes les images dans la galerie
                image_elements = driver.find_elements(By.XPATH, "//div[@class='popup-gallery']//a")
                
                for i, img_element in enumerate(image_elements):
                    img_url = img_element.get_attribute("href")
                    if img_url and img_url.endswith(('.jpg', '.jpeg', '.png')):
                        try:
                            # Télécharger l'image
                            img_response = requests.get(img_url, stream=True)
                            if img_response.status_code == 200:
                                # Extraire le nom de fichier de l'URL
                                img_filename = os.path.basename(img_url)
                                img_path = os.path.join(folder_path, f"{i+1}_{img_filename}")
                                
                                # Sauvegarder l'image
                                with open(img_path, 'wb') as img_file:
                                    for chunk in img_response.iter_content(1024):
                                        img_file.write(chunk)
                                
                                print(f"Image téléchargée: {img_path}")
                            
                        except Exception as e:
                            print(f"Erreur lors du téléchargement de l'image {img_url}: {e}")
            except Exception as e:
                print(f"Erreur lors de la recherche des images: {e}")

            # Ajouter les informations à la liste des voitures
            all_cars_data.append(infos)
            print(f"Annonce {index+1} traitée avec succès")
            
        except Exception as e:
            print(f"Erreur lors du scraping de l'annonce {index+1}: {str(e)}")
            # Ajouter quand même les informations partielles
            all_cars_data.append(infos)
            
    except Exception as e:
        print(f"Erreur lors du traitement de l'annonce {index+1}: {str(e)}")
        continue

# Enregistrer toutes les données dans un fichier CSV
if all_cars_data:
    # Définir l'ordre des colonnes souhaité
    fieldnames = [
        'ID', 'Titre', 'Prix', 'Date de publication', 'Année', 'Type de carburant', 
        'Transmission', 'Créateur', 'Type de véhicule', 'Secteur', 'Kilométrage', 
        'Marque', 'Modèle', 'Nombre de portes', 'Origine', 'Première main', 
        'Puissance fiscale', 'État', 'Équipements', 'Ville du vendeur', 'Dossier d\'images'
    ]
    
    # Écrire le fichier CSV
    with open(output_csv_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_cars_data)
        
    print(f"Les informations ont été enregistrées dans '{output_csv_path}'.")
else:
    print("Aucune donnée n'a été extraite.")

# Fermer le navigateur
driver.quit()
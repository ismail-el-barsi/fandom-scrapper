import json
import logging
import os
import re
import sys
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from flask_cors import CORS

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

import data_cleaner

# Configuration
app = Flask(__name__, static_folder='../frontend', static_url_path='/')
CORS(app)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Mots-clés pour la découverte automatique
CATEGORY_KEYWORDS = [
    'Characters', 'Heroes', 'Villains', 'Personalities', 'Figures', 'People', 'NPCs', 'Bosses', 'Creatures', 'Monsters',
    'Items', 'Weapons', 'Armor', 'Spells', 'Abilities', 'Factions', 'Locations', 'Vehicles',
    'Personnages', 'Champions', 'Héros', 'Créatures', 'Monstres', 'Objets', 'Armes', 'Sorts', 'Lieux'
]
CONTENT_AREA_SELECTORS = [
    'div.category-page__members', 'div.mw-category-group', 'div.category-page__pages',
    'table.wikitable', 'div#mw-content-text'
]
LINK_BLACKLIST_KEYWORDS = [
    '/Trivia', '/Cosmetics', '/Gallery', '/Quotes', '/Development',
    'Minor_Characters', 'List_of', '(Disambiguation)',
    'Category:', 'File:', 'Template:', 'User:', 'Special:', '?action='
]

def find_category_page(base_url):
    """Découvre automatiquement les catégories pertinentes d'un wiki Fandom"""
    logging.info(f"Découverte automatique de catégories pour {base_url}")
    try:
        # Explorer la page principale pour découvrir la structure
        response = requests.get(urljoin(base_url, '/wiki/Main_Page'), headers=HEADERS, timeout=10)
        if response.status_code == 404:
            response = requests.get(base_url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Découvrir automatiquement toutes les catégories disponibles
        discovered_categories = []
        
        # Scanner tous les liens de catégorie présents sur la page actuelle
        all_category_links = soup.find_all('a', href=re.compile(r'/wiki/Category:', re.IGNORECASE))
        
        for link in all_category_links:
            href = link.get('href', '')
            if href:
                category_name = href.split('Category:')[-1].replace('_', ' ')
                link_text = link.get_text(strip=True)
                
                relevance_score = _analyze_category_relevance(category_name, link_text, soup, link)
                
                if relevance_score > 0:
                    discovered_categories.append({
                        'url': urljoin(base_url, href),
                        'name': category_name,
                        'text': link_text,
                        'score': relevance_score
                    })
        
        # Exploration récursive si pas assez de catégories
        if len(discovered_categories) < 5:
            wiki_links = soup.find_all('a', href=re.compile(r'/wiki/(?!Category:|File:|Template:|User:|Special:)', re.IGNORECASE))[:5]
            
            for wiki_link in wiki_links:
                try:
                    explore_url = urljoin(base_url, wiki_link.get('href', ''))
                    explore_response = requests.get(explore_url, headers=HEADERS, timeout=5)
                    if explore_response.status_code == 200:
                        explore_soup = BeautifulSoup(explore_response.text, 'lxml')
                        explore_categories = explore_soup.find_all('a', href=re.compile(r'/wiki/Category:', re.IGNORECASE))
                        
                        for link in explore_categories[:3]:
                            href = link.get('href', '')
                            if href:
                                category_name = href.split('Category:')[-1].replace('_', ' ')
                                link_text = link.get_text(strip=True)
                                
                                relevance_score = _analyze_category_relevance(category_name, link_text, explore_soup, link)
                                
                                if relevance_score > 0:
                                    discovered_categories.append({
                                        'url': urljoin(base_url, href),
                                        'name': category_name,
                                        'text': link_text,
                                        'score': relevance_score + 1  # Bonus léger pour exploration
                                    })
                except:
                    continue
        
        # Déduplication et tri par pertinence
        unique_categories = {}
        for cat in discovered_categories:
            if cat['url'] not in unique_categories or cat['score'] > unique_categories[cat['url']]['score']:
                unique_categories[cat['url']] = cat
        
        sorted_categories = sorted(unique_categories.values(), key=lambda x: x['score'], reverse=True)
        
        logging.info(f"Découvert {len(sorted_categories)} catégories potentielles")
        
        # Test et validation des catégories
        for category in sorted_categories[:10]:
            logging.info(f"Test de catégorie: {category['name']} (score: {category['score']})")
            
            if _validate_category_content(category['url']):
                logging.info(f"Catégorie valide trouvée: {category['name']}")
                return category['url']
        
        logging.warning("Aucune catégorie exploitable découverte automatiquement")
        return None
        
    except requests.RequestException as e:
        logging.error(f"Erreur réseau lors de la découverte de catégories : {e}")
        return None

def _analyze_category_relevance(category_name, link_text, soup, link_element):
    """Analyse la pertinence d'une catégorie"""
    score = 0
    category_lower = category_name.lower()
    text_lower = link_text.lower()
    
    primary_keywords = ['character', 'personnage', 'people', 'individual', 'person']
    secondary_keywords = ['hero', 'villain', 'protagonist', 'antagonist', 'main', 'major']
    content_keywords = ['item', 'weapon', 'armor', 'location', 'place', 'faction', 'group']
    
    # Score pour mots-clés principaux
    for keyword in primary_keywords:
        if keyword in category_lower or keyword in text_lower:
            score += 15
    
    # Score pour mots-clés secondaires
    for keyword in secondary_keywords:
        if keyword in category_lower or keyword in text_lower:
            score += 10
    
    # Score pour mots-clés de contenu
    for keyword in content_keywords:
        if keyword in category_lower or keyword in text_lower:
            score += 8
    
    if any(word in category_lower for word in ['main', 'principal', 'primary', 'core']):
        score += 12
    
    # Pénalité pour les catégories administratives
    admin_keywords = ['stub', 'template', 'maintenance', 'cleanup', 'delete', 'redirect', 'disambiguation']
    for keyword in admin_keywords:
        if keyword in category_lower or keyword in text_lower:
            score -= 20
    
    # Bonus pour position visible
    try:
        page_text = soup.get_text()
        link_position = page_text.find(link_text)
        if link_position != -1 and link_position < len(page_text) * 0.3:
            score += 5
    except:
        pass
    
    # Bonus pour contexte de navigation
    parent_element = link_element.parent
    if parent_element:
        parent_text = parent_element.get_text().lower()
        if any(word in parent_text for word in ['navigation', 'menu', 'browse', 'explore']):
            score += 8
    
    return max(0, score)

def _validate_category_content(category_url):
    """Valide qu'une catégorie contient du contenu exploitable"""
    try:
        response = requests.get(category_url, headers=HEADERS, timeout=8)
        if response.status_code != 200:
            return False
            
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Compter les liens wiki valides
        wiki_links = soup.find_all('a', href=re.compile(r'/wiki/(?!Category:|File:|Template:|User:|Special:)', re.IGNORECASE))
        
        # Filtrer les liens blacklistés
        valid_links = []
        for link in wiki_links:
            href = link.get('href', '')
            if not any(keyword.lower() in href.lower() for keyword in LINK_BLACKLIST_KEYWORDS):
                valid_links.append(link)
        
        # Vérification du contenu minimal
        if len(valid_links) < 10:
            return False
        
        content_indicators = soup.find_all(['div'], class_=re.compile(r'category|mw-category|page-list', re.IGNORECASE))
        if not content_indicators:
            return False
        
        page_text = soup.get_text().lower()
        if 'redirect' in page_text and len(page_text) < 500:
            return False
        
        return True
        
    except:
        return False

def get_all_item_links(category_page_url, scraped_links=None, visited_pages=None):
    """Récupère tous les liens d'articles depuis une page de catégorie"""
    if scraped_links is None: scraped_links = set()
    if visited_pages is None: visited_pages = set()
    if category_page_url in visited_pages: return list(scraped_links)
    logging.info(f"Scraping des liens depuis : {category_page_url}")
    visited_pages.add(category_page_url)
    try:
        response = requests.get(category_page_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        content_area = None
        for selector in CONTENT_AREA_SELECTORS:
            content_area = soup.select_one(selector)
            if content_area: break
        if not content_area: return list(scraped_links)

        base_domain = f"https://{urlparse(category_page_url).netloc}"
        for a in content_area.find_all('a', href=True):
            if '/wiki/' in a['href']:
                href = a['href']
                if not any(keyword.lower() in href.lower() for keyword in LINK_BLACKLIST_KEYWORDS):
                     scraped_links.add(urljoin(base_domain, href))

        # Pagination
        next_page_link = soup.find('a', class_='category-page__pagination-next') or \
                         soup.find('a', string=re.compile(r'^\s*next( page)?\s*$', re.IGNORECASE))
        if next_page_link and 'href' in next_page_link.attrs:
            next_page_url = urljoin(category_page_url, next_page_link['href'])
            return get_all_item_links(next_page_url, scraped_links, visited_pages)
        return list(scraped_links)
    except requests.RequestException as e:
        logging.error(f"Erreur réseau lors de la récupération des liens : {e}")
        return list(scraped_links)

def scrape_page_data(page_url):
    """Extrait les données d'une page wiki"""
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Recherche de l'infobox
        infobox = soup.find('aside', class_=re.compile(r'portable-infobox|pi-theme|infobox', re.IGNORECASE))
        if not infobox:
            infobox = soup.find('table', class_=re.compile(r'infobox', re.IGNORECASE))
        if not infobox:
            return None, "Infobox non trouvée"
        
        # Extraction du nom
        name_tag = soup.find('h1', id='firstHeading')
        name = name_tag.get_text(strip=True) if name_tag else "Nom non trouvé"
        
        # Extraction d'image
        raw_image_url = None
        
        # Image principale de l'infobox
        image_container = infobox.find(class_='pi-image')
        if image_container:
            image_tag = image_container.find('img')
            if image_tag:
                raw_image_url = image_tag.get('data-src') or image_tag.get('src')
        
        # Première image dans l'infobox
        if not raw_image_url:
            image_tag = infobox.find('img')
            if image_tag:
                raw_image_url = image_tag.get('data-src') or image_tag.get('src')
        
        # Image dans le contenu principal
        if not raw_image_url:
            content_area = soup.find('div', {'id': 'mw-content-text'})
            if content_area:
                image_tag = content_area.find('img')
                if image_tag:
                    raw_image_url = image_tag.get('data-src') or image_tag.get('src')
        
        # Nettoyage de l'URL d'image
        image_url = None
        if raw_image_url:
            # Supprimer les paramètres de redimensionnement
            cleaned_url = re.sub(r'/scale-to-width-down/\d+', '', raw_image_url)
            cleaned_url = re.sub(r'/revision/latest.*', '', cleaned_url)
            cleaned_url = cleaned_url.split('/revision')[0]
            
            if cleaned_url.startswith('http'):
                image_url = cleaned_url
            elif cleaned_url.startswith('//'):
                image_url = 'https:' + cleaned_url
            else:
                image_url = urljoin(page_url, cleaned_url)
        
        if not image_url or not image_url.startswith('http'):
            return None, f"Image principale invalide pour {name}"

        # Extraction des attributs améliorée
        attributes = {}
        
        # Méthode 1: data-source attributes
        for item in infobox.find_all('div', {'data-source': True}):
            key = item['data-source'].replace('_', ' ').title()
            value_tag = item.find('div', class_='pi-data-value') or item.find('span') or item
            if key and value_tag:
                value = value_tag.get_text(strip=True, separator=' | ')
                attributes[key] = value
        
        # Méthode 2: pi-data structure
        if not attributes:
            for item in infobox.find_all('div', class_=re.compile(r'pi-item|pi-data', re.IGNORECASE)):
                key_tag = item.find(['h3', 'div'], class_=re.compile(r'pi-data-label', re.IGNORECASE))
                value_tag = item.find('div', class_=re.compile(r'pi-data-value', re.IGNORECASE))
                if key_tag and value_tag:
                    key = key_tag.get_text(strip=True)
                    value = value_tag.get_text(strip=True, separator=' | ')
                    attributes[key] = value
        
        # Méthode 3: table infobox classique
        if not attributes:
            for row in infobox.find_all('tr'):
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True, separator=' | ')
                    if key and value:
                        attributes[key] = value
        
        # Nettoyage des attributs
        cleaned_attributes = data_cleaner.data_cleaner.clean_attributes_dict(attributes)
        
        # Extraction de description
        description = data_cleaner.data_cleaner.extract_enhanced_description(soup, infobox)
        
        # Extraction de rôle
        main_role = data_cleaner.data_cleaner.extract_smart_role(cleaned_attributes, soup)
        
        result = {
            "name": name,
            "image_url": image_url,
            "description": description,
            "role": main_role,
            "attributes": cleaned_attributes,
            "source_url": page_url
        }
        
        return result, None
        
    except requests.RequestException as e:
        return None, f"Erreur réseau: {e}"
    except Exception as e:
        return None, f"Erreur de parsing: {e}"

def validate_and_clean_result(result):
    """Validation et nettoyage des résultats"""
    return data_cleaner.data_cleaner.validate_and_clean_result(result)

def generate_data_quality_stats(results):
    """Génération des statistiques de qualité"""
    return data_cleaner.data_cleaner.generate_quality_statistics(results)

@app.route('/api/scrape', methods=['POST'])
def scrape_fandom():
    """API endpoint pour lancer le scraping d'un wiki Fandom"""
    start_time = time.time()
    data = request.json
    fandom_url_input = data.get('fandom_url')
    if not fandom_url_input: 
        return jsonify({"error": "URL du fandom manquante"}), 400
    
    try:
        parsed_url = urlparse(fandom_url_input)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        fandom_name = parsed_url.netloc.split('.')[0]
    except Exception as e: 
        return jsonify({"error": f"URL invalide : {e}"}), 400
    
    category_page = find_category_page(base_url)
    if not category_page: 
        return jsonify({"error": "Impossible de trouver une page de catégorie de départ fiable."}), 500
    
    all_links = get_all_item_links(category_page)
    filtered_links = [link for link in all_links if not any(keyword.lower() in link.lower() for keyword in LINK_BLACKLIST_KEYWORDS)]
    links_to_scrape = filtered_links[:50]
    logging.info(f"Scraping des {len(links_to_scrape)} premiers liens...")

    results, errors = [], []
    for i, link in enumerate(links_to_scrape):
        data, error = scrape_page_data(link)
        if data:
            cleaned_data = validate_and_clean_result(data)
            if cleaned_data:
                results.append(cleaned_data)
            else:
                errors.append({"url": link, "reason": "Données invalides après nettoyage"})
        else: 
            errors.append({"url": link, "reason": error})
        time.sleep(0.05)
    
    # Si moins de 10 fiches valides, essayer d'autres catégories
    MIN_VALID_FICHES = 10
    used_category = "Catégorie principale"
    
    if len(results) < MIN_VALID_FICHES:
        logging.info(f"Seulement {len(results)} fiches trouvées, recherche d'autres catégories...")
        
        # Sauvegarder les résultats de la première catégorie
        first_category_results = results.copy()
        first_category_errors = errors.copy()
        
        # Chercher d'autres catégories
        try:
            # Utiliser le même mécanisme que find_category_page mais récupérer plusieurs catégories
            response = requests.get(urljoin(base_url, '/wiki/Main_Page'), headers=HEADERS, timeout=10)
            if response.status_code == 404:
                response = requests.get(base_url, headers=HEADERS, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                discovered_categories = []
                
                # Scanner tous les liens de catégorie
                all_category_links = soup.find_all('a', href=re.compile(r'/wiki/Category:', re.IGNORECASE))
                
                for link in all_category_links[:5]:  # Limiter à 5 catégories alternatives
                    href = link.get('href', '')
                    if href:
                        category_name = href.split('Category:')[-1].replace('_', ' ')
                        category_url = urljoin(base_url, href)
                        
                        # Vérifier que ce n'est pas la même catégorie que celle déjà utilisée
                        if category_url != category_page:
                            discovered_categories.append({
                                'url': category_url,
                                'name': category_name
                            })
                
                # Tester les catégories alternatives
                for category_info in discovered_categories:
                    category_page_alt = category_info['url']
                    category_name = category_info['name']
                    
                    logging.info(f"Test de la catégorie alternative: {category_name}")
                    
                    try:
                        alt_links = get_all_item_links(category_page_alt)
                        alt_filtered = [link for link in alt_links if not any(keyword.lower() in link.lower() for keyword in LINK_BLACKLIST_KEYWORDS)]
                        alt_to_scrape = alt_filtered[:30]  # Limite réduite pour les catégories alternatives
                        
                        alt_results = []
                        alt_errors = []
                        
                        for link in alt_to_scrape:
                            data, error = scrape_page_data(link)
                            if data:
                                cleaned_data = validate_and_clean_result(data)
                                if cleaned_data:
                                    alt_results.append(cleaned_data)
                                else:
                                    alt_errors.append({"url": link, "reason": "Données invalides après nettoyage"})
                            else: 
                                alt_errors.append({"url": link, "reason": error})
                            time.sleep(0.05)
                        
                        logging.info(f"Catégorie {category_name}: {len(alt_results)} fiches trouvées")
                        
                        # Si cette catégorie a plus de fiches, l'utiliser
                        if len(alt_results) > len(results):
                            results = alt_results
                            errors = alt_errors
                            used_category = category_name
                        
                        # Si on a atteint le minimum, s'arrêter
                        if len(alt_results) >= MIN_VALID_FICHES:
                            results = alt_results
                            errors = alt_errors
                            used_category = category_name
                            logging.info(f"Minimum atteint avec {category_name}!")
                            break
                            
                    except Exception as e:
                        logging.warning(f"Erreur avec la catégorie {category_name}: {e}")
                        continue
        
        except Exception as e:
            logging.warning(f"Erreur lors de la recherche de catégories alternatives: {e}")
    
    total_time = time.time() - start_time
    
    quality_stats = generate_data_quality_stats(results)
    
    report = f"""# Rapport de Scraping pour : {fandom_name}
- **Temps total :** {total_time:.2f}s
- **Fiches OK :** {len(results)}
- **Fiches KO :** {len(errors)}
- **Catégorie utilisée :** {used_category}

{quality_stats}

## Fiches échouées
"""
    for err in errors: 
        report += f"- URL: {err['url']}\n  - Raison: {err['reason']}\n"
    
    with open(os.path.join(DATA_DIR, f'{fandom_name}_report.md'), 'w', encoding='utf-8') as f: 
        f.write(report)
    with open(os.path.join(DATA_DIR, f'{fandom_name}_data.json'), 'w', encoding='utf-8') as f: 
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Scraping terminé. {len(results)} fiches sauvegardées.")
    return jsonify(results)

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
        
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

# On importe les fonctions de scraping
from scraper.app import (LINK_BLACKLIST_KEYWORDS, find_category_page,
                         generate_data_quality_stats, get_all_item_links,
                         scrape_page_data, validate_and_clean_result)
from scraper.data_cleaner import data_cleaner

# --- Configuration ---
FANDOM_LIST_FILE = 'fandoms_a_tester.txt'
PAGES_TO_SCRAPE_PER_FANDOM = 50
MAX_WORKERS = 10

# Configuration du dossier de sortie des données
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Configuration du logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')


def process_fandom(base_url):
    start_time = time.time()
    
    if base_url.strip().startswith('#') or not base_url.strip():
        return True, {"message": f"Ligne ignorée (commentaire) : {base_url}"}

    try:
        fandom_name = urlparse(base_url).netloc.split('.')[0]
    except Exception:
        return False, {"message": f"URL invalide : {base_url}"}
        
    print(f"--- Traitement de : {fandom_name} ---")

    try:
        category_page = find_category_page(base_url)
        if not category_page:
            return False, {"message": "Échec : Impossible de trouver la page de catégorie de départ."}

        all_links = get_all_item_links(category_page)
        total_links_found = len(all_links)
        if not all_links:
            return False, {"message": "Échec : Aucun lien trouvé sur la page de catégorie."}

        filtered_links = [link for link in all_links if not any(keyword.lower() in link.lower() for keyword in LINK_BLACKLIST_KEYWORDS)]
        links_to_scrape = filtered_links[:PAGES_TO_SCRAPE_PER_FANDOM]
        
        if not links_to_scrape:
            return False, {"message": "Échec : Aucun lien valide à scraper après filtrage.", "total_links": total_links_found}

        print(f"  -> {len(links_to_scrape)}/{total_links_found} fiches à scraper pour {fandom_name}...")

        results = []
        errors = []
        skipped_invalid = 0
        
        for i, link in enumerate(links_to_scrape):
            print(f"  -> {fandom_name} [{i+1}/{len(links_to_scrape)}]", end='\r')
            data, error = scrape_page_data(link)
            if data:
                # Valider et nettoyer les données avec les nouvelles fonctions
                cleaned_data = validate_and_clean_result(data)
                if cleaned_data:
                    results.append(cleaned_data)
                else:
                    skipped_invalid += 1
                    errors.append({"url": link, "reason": "Données invalides après nettoyage et validation"})
            else:
                errors.append({"url": link, "reason": error})
            time.sleep(0.05)
        
        print(" " * 60, end='\r')

        # Si moins de 10 fiches valides, essayer d'autres catégories
        MIN_VALID_FICHES = 10
        used_category = "Catégorie principale"
        categories_tested = ["Catégorie principale"]
        
        if len(results) < MIN_VALID_FICHES:
            print(f"  -> Seulement {len(results)} fiches trouvées, recherche d'autres catégories...")
            
            try:
                # Chercher d'autres catégories depuis la page principale
                from urllib.parse import urljoin

                import requests
                from bs4 import BeautifulSoup
                
                response = requests.get(urljoin(base_url, '/wiki/Main_Page'), headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                if response.status_code == 404:
                    response = requests.get(base_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    discovered_categories = []
                    
                    # Scanner les liens de catégorie
                    all_category_links = soup.find_all('a', href=re.compile(r'/wiki/Category:', re.IGNORECASE))
                    
                    for link in all_category_links[:5]:  # Limiter à 5 catégories
                        href = link.get('href', '')
                        if href:
                            category_name = href.split('Category:')[-1].replace('_', ' ')
                            category_url = urljoin(base_url, href)
                            
                            # Vérifier que ce n'est pas la même catégorie
                            if category_url != category_page:
                                discovered_categories.append({
                                    'url': category_url,
                                    'name': category_name
                                })
                    
                    # Tester les catégories alternatives
                    for category_info in discovered_categories:
                        if len(results) >= MIN_VALID_FICHES:
                            break
                            
                        category_page_alt = category_info['url']
                        category_name = category_info['name']
                        categories_tested.append(category_name)
                        
                        print(f"  -> Test catégorie: {category_name}")
                        
                        try:
                            alt_links = get_all_item_links(category_page_alt)
                            alt_filtered = [link for link in alt_links if not any(keyword.lower() in link.lower() for keyword in LINK_BLACKLIST_KEYWORDS)]
                            alt_to_scrape = alt_filtered[:20]  # Limite réduite
                            
                            alt_results = []
                            alt_errors = []
                            alt_skipped = 0
                            
                            for link in alt_to_scrape:
                                data, error = scrape_page_data(link)
                                if data:
                                    cleaned_data = validate_and_clean_result(data)
                                    if cleaned_data:
                                        alt_results.append(cleaned_data)
                                    else:
                                        alt_skipped += 1
                                        alt_errors.append({"url": link, "reason": "Données invalides après nettoyage et validation"})
                                else:
                                    alt_errors.append({"url": link, "reason": error})
                                time.sleep(0.05)
                            
                            print(f"    -> {category_name}: {len(alt_results)} fiches trouvées")
                            
                            # Si cette catégorie a plus de fiches, l'utiliser
                            if len(alt_results) > len(results):
                                results = alt_results
                                errors = alt_errors
                                skipped_invalid = alt_skipped
                                used_category = category_name
                            
                            # Si on a atteint le minimum, s'arrêter
                            if len(alt_results) >= MIN_VALID_FICHES:
                                results = alt_results
                                errors = alt_errors
                                skipped_invalid = alt_skipped
                                used_category = category_name
                                print(f"    -> ✅ Minimum atteint avec {category_name}!")
                                break
                                
                        except Exception as e:
                            print(f"    -> Erreur avec {category_name}: {e}")
                            continue
            
            except Exception as e:
                print(f"  -> Erreur lors de la recherche d'alternatives: {e}")

        if not results:
            return False, {
                "message": f"Échec : Aucune fiche valide après nettoyage. {skipped_invalid} fiches rejetées pour qualité insuffisante.", 
                "total_links": total_links_found,
                "skipped_invalid": skipped_invalid
            }

        total_time = time.time() - start_time
        
        # Déterminer le statut de succès/échec
        success_status = len(results) >= MIN_VALID_FICHES
        
        # Message de statut
        if success_status:
            status_message = f"✅ SUCCÈS - {len(results)} fiches valides (minimum requis: {MIN_VALID_FICHES})"
        else:
            status_message = f"⚠️ PARTIELLEMENT RÉUSSI - {len(results)} fiches valides (minimum requis: {MIN_VALID_FICHES})"
        
        # Générer des statistiques
        quality_stats = generate_data_quality_stats(results)
        
        report = f"""# Rapport de Scraping pour : {fandom_name}
- **Statut :** {status_message}
- **Temps total :** {total_time:.2f}s
- **Catégories testées :** {len(categories_tested)} ({', '.join(categories_tested)})
- **Catégorie utilisée :** {used_category}
- **Liens trouvés :** {total_links_found}
- **Liens scrapés :** {len(links_to_scrape)}
- **Fiches OK :** {len(results)}
- **Fiches KO :** {len(errors)}
- **Fiches rejetées (qualité) :** {skipped_invalid}
- **Taux de succès :** {len(results)/len(links_to_scrape)*100:.1f}%

{quality_stats}

## Fiches échouées
"""
        for err in errors:
            report += f"- URL: {err.get('url', 'N/A')}\n  - Raison: {err.get('reason', 'N/A')}\n"
        
        report_path = os.path.join(DATA_DIR, f'{fandom_name}_report.md')
        json_path = os.path.join(DATA_DIR, f'{fandom_name}_data.json')
        
        with open(report_path, 'w', encoding='utf-8') as f: f.write(report)
        with open(json_path, 'w', encoding='utf-8') as f: json.dump(results, f, indent=2, ensure_ascii=False)
        
        return True, {
            "message": f"{status_message} - Catégorie utilisée: {used_category}",
            "total_links": total_links_found,
            "valid_results": len(results),
            "skipped_invalid": skipped_invalid,
            "success_rate": len(results)/len(links_to_scrape)*100 if links_to_scrape else 0,
            "categories_tested": categories_tested,
            "used_category": used_category,
            "minimum_reached": success_status
        }

    except Exception as e:
        return False, {"message": f"Erreur critique inattendue : {e}"}


def main():
    """Fonction principale pour lancer le scraping de masse."""
    try:
        with open(FANDOM_LIST_FILE, 'r', encoding='utf-8') as f:
            fandom_urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"ERREUR : Le fichier '{FANDOM_LIST_FILE}' est introuvable.")
        return

    print(f"=== Lancement du scraping de masse sur {len(fandom_urls)} Fandoms avec {MAX_WORKERS} workers en parallèle ===")
    
    success_list = []
    failure_list = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(process_fandom, url): url for url in fandom_urls}
        
        for future in future_to_url:
            url = future_to_url[future]
            try:
                is_success, result_dict = future.result()
                if is_success:
                    success_list.append((url, result_dict))
                else:
                    failure_list.append((url, result_dict))
            except Exception as e:
                failure_list.append((url, {"message": f"Erreur lors de l'exécution du scraping : {e}"}))
    
    total_time = time.time() - start_time

    # --- Affichage du rapport final ---
    print("\n\n" + "="*35)
    print("=== RAPPORT DE SCRAPING FINAL ===")
    print("="*35)
    print(f"Temps total d'exécution : {total_time:.2f} secondes")
    
    successful_runs = [item for item in success_list if not item[1]["message"].startswith('Ligne ignorée')]
    
    # Calculer les statistiques globales
    total_valid_results = sum(item[1].get('valid_results', 0) for item in successful_runs)
    total_skipped = sum(item[1].get('skipped_invalid', 0) for item in successful_runs)
    total_links_found = sum(item[1].get('total_links', 0) for item in successful_runs)
    average_success_rate = sum(item[1].get('success_rate', 0) for item in successful_runs) / len(successful_runs) if successful_runs else 0
    
    print(f"Fandoms traités : {len(successful_runs) + len(failure_list)}")
    print(f"✅ Fichiers générés avec succès : {len(successful_runs)}")
    print(f"❌ Échecs : {len(failure_list)}")
    print(f"📊 Total fiches valides : {total_valid_results}")
    print(f"🚫 Total fiches rejetées : {total_skipped}")
    print(f"🔍 Total liens trouvés : {total_links_found}")
    print(f"📈 Taux de succès moyen : {average_success_rate:.1f}%")
    print("-" * 35)

    if failure_list:
        print("\n--- DÉTAIL DES ÉCHECS ---")
        for url, result_dict in failure_list:
            print(f"- {url}\n  Raison : {result_dict['message']}\n")

    if successful_runs:
        print("\n--- DÉTAIL DES SUCCÈS ---")
        for url, result_dict in successful_runs:
            total_links = result_dict.get('total_links', 'N/A')
            valid_results = result_dict.get('valid_results', 'N/A')
            skipped = result_dict.get('skipped_invalid', 'N/A')
            success_rate = result_dict.get('success_rate', 0)
            
            print(f"- {url}")
            print(f"  📊 {valid_results} fiches valides | {skipped} rejetées | {total_links} liens trouvés")
            print(f"  📈 Taux de succès: {success_rate:.1f}%")
            print()

    print("\nLe scraping de masse est terminé. Vérifiez votre dossier '/data' pour les fichiers JSON et les rapports.")
    
    # Afficher un résumé de qualité si on a des données
    if total_valid_results > 0:
        quality_ratio = (total_valid_results / (total_valid_results + total_skipped)) * 100 if (total_valid_results + total_skipped) > 0 else 0
        print(f"\n🎯 RÉSUMÉ QUALITÉ : {quality_ratio:.1f}% des données scrapées sont de qualité suffisante")
        print(f"💡 CONSEIL : Consultez les rapports .md dans le dossier '/data' pour voir les détails de qualité par fandom")

if __name__ == '__main__':
    main()
    
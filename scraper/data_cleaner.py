
import logging
import re
from typing import Dict, List, Optional, Tuple


class DataCleaner:
    
    def __init__(self):
        # Patterns de nettoyage améliorés
        self.reference_pattern = re.compile(r'\[\s*(?:note\s*)?\d+\s*\]|\[\d+\]', re.IGNORECASE)
        self.pipe_separator_pattern = re.compile(r'\s*\|\s*')
        self.wiki_link_pattern = re.compile(r'\[\[([^|\]]+\|)?([^\]]+)\]\]')
        self.extra_spaces_pattern = re.compile(r'\s+')
        self.unwanted_chars_pattern = re.compile(r'^[\[\(\)\]\-:\s]+|[\[\(\)\]\-:\s]+$')
        
        # Nouveaux patterns pour détecter les problèmes
        self.truncated_pattern = re.compile(r'\.{2,}$')  # Détecte ... à la fin
        self.infobox_pattern = re.compile(r'(InformationSource|BiographicalInformation|HealthEnergy|Sell\s*Price)', re.IGNORECASE)
        self.malformed_desc_pattern = re.compile(r'[A-Z][a-z]+[A-Z][a-z]+[A-Z]')  # CamelCase suspect
        
        # Préfixes à supprimer des clés d'attributs
        self.key_prefixes_to_remove = [
            'Type', 'Home', 'Race', 'Gender', 'Age', 'Affiliation', 'Occupation', 
            'Hair', 'Eye', 'Weapon', 'Job', 'Status', 'Predecessor', 'First', 'Last',
            'Row \\d+ Info', 'Cell \\d+ Info', 'Block\\d+', 'End.*', 'Image', 'Caption',
            'Color', 'Height', 'Weight', 'Born', 'Death', 'World', 'Ship', 'Voice'
        ]
        
        # Mots-clés pour identifier les rôles
        self.role_keywords = [
            'type', 'role', 'class', 'occupation', 'job', 'status', 'position', 'rank'
        ]
        
        # Catégories d'attributs pour l'organisation
        self.attribute_categories = {
            'identity': [
                'name', 'full name', 'real name', 'alias', 'aliases', 'nickname', 
                'species', 'race', 'gender', 'age', 'born', 'birth'
            ],
            'appearance': [
                'hair', 'eye', 'eyes', 'height', 'weight', 'appearance', 'color',
                'skin', 'build', 'style'
            ],
            'origin': [
                'origin', 'homeworld', 'home', 'world', 'birthplace', 'nationality', 
                'region', 'planet', 'dimension', 'realm'
            ],
            'affiliation': [
                'affiliation', 'organization', 'faction', 'team', 'guild', 'clan',
                'army', 'group', 'alliance', 'membership'
            ],
            'status': [
                'status', 'occupation', 'job', 'profession', 'class', 'rank', 
                'position', 'title', 'role'
            ],
            'abilities': [
                'abilities', 'powers', 'skills', 'weapon', 'weapons', 'magic', 
                'special', 'equipment', 'gear', 'items'
            ],
            'relationships': [
                'family', 'relatives', 'parents', 'siblings', 'children', 'friends', 
                'enemies', 'allies', 'spouse', 'partner'
            ],
            'media': [
                'first', 'latest', 'debut', 'appearance', 'games', 'movies', 'series',
                'voice actor', 'actor', 'portrayed'
            ]
        }

    def clean_text_content(self, text: str) -> str:
        """Nettoie le contenu textuel des références et caractères indésirables"""
        if not text:
            return ""
        
        # Supprimer les références wiki [1], [note 1], etc.
        text = self.reference_pattern.sub('', text)
        
        # Supprimer les liens wiki internes [[link|text]] -> text
        text = self.wiki_link_pattern.sub(r'\\2', text)
        
        # Traitement spécial des séparateurs pipe
        text = self._clean_pipe_separators(text)
        
        # Nettoyer les espaces multiples
        text = self.extra_spaces_pattern.sub(' ', text)
        
        # Supprimer les caractères indésirables en début et fin
        text = self.unwanted_chars_pattern.sub('', text)
        
        # Nettoyer les parenthèses orphelines ou mal fermées
        text = re.sub(r'\\(\\s*\\)', '', text)  # Supprimer les parenthèses vides
        text = re.sub(r'\\[\\s*\\]', '', text)  # Supprimer les crochets vides
        
        return text.strip()

    def _clean_pipe_separators(self, text: str) -> str:
        """Nettoie intelligemment les séparateurs pipe"""
        # Si le texte contient beaucoup de pipes, c'est probablement du contenu mal formaté
        pipe_count = text.count('|')
        if pipe_count > 3:
            # Remplacer les pipes par des espaces, mais garder la structure logique
            # Exemple: "Human | (enhanced | with | DNA)" -> "Human (enhanced with DNA)"
            
            # Préserver les structures entre parenthèses et crochets
            parts = []
            current_part = ""
            in_parentheses = 0
            in_brackets = 0
            
            i = 0
            while i < len(text):
                char = text[i]
                
                if char == '(':
                    in_parentheses += 1
                elif char == ')':
                    in_parentheses -= 1
                elif char == '[':
                    in_brackets += 1
                elif char == ']':
                    in_brackets -= 1
                elif char == '|' and in_parentheses == 0 and in_brackets == 0:
                    # Pipe en dehors de parenthèses/crochets = séparateur principal
                    if current_part.strip():
                        parts.append(current_part.strip())
                    current_part = ""
                    i += 1
                    continue
                elif char == '|' and (in_parentheses > 0 or in_brackets > 0):
                    # Pipe dans des parenthèses/crochets = remplacer par espace
                    current_part += ' '
                    i += 1
                    continue
                
                current_part += char
                i += 1
            
            if current_part.strip():
                parts.append(current_part.strip())
            
            # Rejoindre les parties principales avec des espaces
            return ' '.join(parts)
        else:
            # Peu de pipes, remplacer simplement par des espaces
            return self.pipe_separator_pattern.sub(' ', text)

    def clean_attribute_key(self, key: str) -> Optional[str]:
        """Nettoie et normalise les clés d'attributs"""
        if not key:
            return None
        
        cleaned_key = key
        
        # Supprimer les préfixes redondants
        for prefix in self.key_prefixes_to_remove:
            pattern = f'^{prefix}\\\\s*'
            cleaned_key = re.sub(pattern, '', cleaned_key, flags=re.IGNORECASE)
        
        # Nettoyer le texte
        cleaned_key = self.clean_text_content(cleaned_key)
        
        # Normaliser la casse (Title Case)
        if cleaned_key:
            cleaned_key = cleaned_key.title()
        
        # Retourner None si la clé est trop courte ou vide
        if not cleaned_key or len(cleaned_key) < 2:
            return None
            
        return cleaned_key

    def clean_attribute_value(self, value: str) -> Optional[str]:
        """Nettoie les valeurs d'attributs avec détection des problèmes"""
        if not value:
            return None
        
        # Détecter les valeurs tronquées
        if self.truncated_pattern.search(value):
            logging.warning(f"Valeur tronquée détectée: {value[:50]}...")
        
        # Nettoyer le contenu textuel
        cleaned_value = self.clean_text_content(value)
        
        # Séparer les informations multilingues
        cleaned_value = self._separate_multilingual_content(cleaned_value)
        
        # Supprimer les valeurs inutiles
        useless_values = ['n/a', 'na', 'unknown', 'none', 'null', '-', '?', '...']
        if cleaned_value.lower() in useless_values:
            return None
        
        # Retourner None si la valeur est trop courte
        if len(cleaned_value) < 2:
            return None
        
        # Limiter la longueur des valeurs
        if len(cleaned_value) > 200:
            cleaned_value = cleaned_value[:197] + '...'
        
        return cleaned_value

    def _separate_multilingual_content(self, text: str) -> str:
        """Sépare le contenu multilingue et garde la version principale"""
        # Pattern pour détecter contenu japonais/chinois avec termes techniques
        multilingual_pattern = re.compile(r'([^a-zA-Z0-9\\s\\-\\(\\)]+)\\s*\\(\\s*([^)]+)\\s*\\)', re.UNICODE)
        
        # Si on trouve du contenu multilingue, garder la version entre parenthèses (généralement anglais)
        match = multilingual_pattern.search(text)
        if match:
            # Garder la version en parenthèses si elle semble être en anglais
            parentheses_content = match.group(2)
            if all(ord(char) < 128 for char in parentheses_content):
                return parentheses_content.strip()
        
        return text

    def clean_attributes_dict(self, attributes: Dict[str, str]) -> Dict[str, str]:
        """Nettoie un dictionnaire d'attributs"""
        cleaned = {}
        
        for key, value in attributes.items():
            # Nettoyer la clé et la valeur
            clean_key = self.clean_attribute_key(key)
            clean_value = self.clean_attribute_value(value)
            
            # Ajouter seulement si les deux sont valides
            if clean_key and clean_value:
                cleaned[clean_key] = clean_value
        
        return cleaned

    def extract_enhanced_description(self, soup, infobox) -> str:
        """Extraction améliorée de description sans contamination d'infobox"""
        descriptions = []
        
        # Obtenir le texte de l'infobox pour éviter la duplication
        infobox_text = infobox.get_text() if infobox else ""
        infobox_words = set(infobox_text.lower().split()) if infobox_text else set()
        
        # Chercher les descriptions dans différents endroits
        content_selectors = [
            'div#mw-content-text p',
            'div.mw-parser-output > p',
            'div.WikiaArticle p',
            'div.page-content p'
        ]
        
        for selector in content_selectors:
            paragraphs = soup.select(selector)
            for p in paragraphs[:3]:  # Examiner les 3 premiers paragraphes
                text = p.get_text(strip=True)
                
                # Filtrer les descriptions de faible qualité
                if (len(text) > 20 and 
                    not self._is_low_quality_description(text) and
                    not self._is_infobox_contaminated(text, infobox_words)):
                    descriptions.append(text)
        
        if descriptions:
            # Prendre la meilleure description
            best_desc = max(descriptions, key=len)
            
            # Nettoyer la description
            best_desc = self.clean_text_content(best_desc)
            
            # Détecter et signaler les descriptions malformées
            if self.infobox_pattern.search(best_desc) or self.malformed_desc_pattern.search(best_desc):
                logging.warning(f"Description malformée détectée: {best_desc[:100]}...")
                # Essayer de nettoyer automatiquement
                best_desc = self._clean_malformed_description(best_desc)
            
            # Limiter la longueur
            if len(best_desc) > 500:
                best_desc = best_desc[:497] + '...'
            
            return best_desc
        
        return "Description non trouvée."

    def _is_infobox_contaminated(self, text: str, infobox_words: set) -> bool:
        """Vérifie si le texte contient trop de mots de l'infobox"""
        if not infobox_words:
            return False
        
        text_words = set(text.lower().split())
        overlap = len(text_words.intersection(infobox_words))
        return overlap > len(text_words) * 0.5  # Plus de 50% de chevauchement
    
    def _clean_malformed_description(self, text: str) -> str:
        """Nettoie les descriptions malformées"""
        # Supprimer les patterns d'infobox collés
        text = self.infobox_pattern.sub('', text)
        
        # Supprimer les mots en CamelCase suspects
        text = re.sub(r'\\b[A-Z][a-z]+[A-Z][a-z]+\\b', '', text)
        
        # Nettoyer les espaces multiples
        text = self.extra_spaces_pattern.sub(' ', text)
        
        return text.strip()

    def _is_low_quality_description(self, desc: str) -> bool:
        """Détermine si une description est de faible qualité"""
        low_quality_indicators = [
            'redirect', 'disambig', 'stub', 'category:', 'template:',
            'see also', 'main article:', 'this article', 'this page',
            'biography information', 'physical description', 'gameplay details'
        ]
        
        desc_lower = desc.lower()
        return any(indicator in desc_lower for indicator in low_quality_indicators)

    def extract_smart_role(self, attributes: Dict[str, str], soup) -> str:
        """Extraction intelligente du rôle avec de meilleures priorités"""
        # 1. Chercher dans les attributs nettoyés avec priorités spécifiques
        priority_keys = ['position', 'title', 'occupation', 'profession', 'class', 'rank', 'status']
        for priority_key in priority_keys:
            for attr_key, attr_value in attributes.items():
                if priority_key in attr_key.lower() and attr_value:
                    clean_role = self.clean_attribute_value(attr_value)
                    if clean_role and len(clean_role) > 2 and clean_role not in ['Characters', 'Hero', 'Personnage']:
                        return clean_role
        
        # 2. Analyser le contexte de la page pour des rôles spécifiques
        page_title = soup.find('h1', id='firstHeading')
        if page_title:
            title_text = page_title.get_text().lower()
            
            # Rôles spécifiques par domaine
            specific_roles = {
                'games': ['player character', 'npc', 'boss', 'antagonist', 'protagonist'],
                'anime': ['main character', 'supporting character', 'villain', 'hero'],
                'tv': ['main cast', 'recurring character', 'guest star'],
                'movies': ['lead actor', 'supporting actor', 'director']
            }
            
            for domain, roles in specific_roles.items():
                for role in roles:
                    if role in title_text:
                        return role.title()
        
        # 3. Chercher dans les catégories de la page
        categories = soup.find_all('a', href=re.compile(r'/wiki/Category:'))
        for cat in categories:
            cat_text = cat.get_text(strip=True).lower()
            if any(word in cat_text for word in ['character', 'protagonist', 'antagonist', 'villain', 'hero']):
                # Extraire le rôle spécifique de la catégorie
                if 'main' in cat_text:
                    return "Main Character"
                elif 'supporting' in cat_text:
                    return "Supporting Character"
                elif 'villain' in cat_text:
                    return "Villain"
                elif 'hero' in cat_text:
                    return "Hero"
        
        # 4. Rôle par défaut plus spécifique selon le fandom
        fandom_type = self._detect_fandom_type(soup)
        if fandom_type == 'game':
            return "Game Character"
        elif fandom_type == 'anime':
            return "Anime Character"
        elif fandom_type == 'tv':
            return "TV Character"
        else:
            return "Character"
    
    def _detect_fandom_type(self, soup) -> str:
        """Détecte le type de fandom basé sur des indices dans la page"""
        # Analyser l'URL et le contenu pour détecter le type
        page_content = soup.get_text().lower()
        
        if any(word in page_content for word in ['gameplay', 'playable', 'game mechanics', 'level']):
            return 'game'
        elif any(word in page_content for word in ['anime', 'manga', 'episode', 'chapter']):
            return 'anime'
        elif any(word in page_content for word in ['season', 'episode', 'aired', 'television']):
            return 'tv'
        else:
            return 'general'

    def organize_attributes_by_category(self, attributes: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Organise les attributs par catégories logiques"""
        organized = {category: {} for category in self.attribute_categories.keys()}
        organized['other'] = {}
        
        for key, value in attributes.items():
            categorized = False
            key_lower = key.lower()
            
            # Chercher dans quelle catégorie placer cet attribut
            for category, keywords in self.attribute_categories.items():
                if any(keyword in key_lower for keyword in keywords):
                    organized[category][key] = value
                    categorized = True
                    break
            
            # Si pas de catégorie trouvée, mettre dans 'other'
            if not categorized:
                organized['other'][key] = value
        
        # Supprimer les catégories vides
        return {k: v for k, v in organized.items() if v}

    def validate_and_clean_result(self, result: Dict) -> Optional[Dict]:
        """Valide et nettoie un résultat final avec détection avancée des problèmes"""
        if not result:
            return None
        
        # Nettoyer les attributs et détecter les duplications
        attributes = result.get('attributes', {})
        if attributes:
            cleaned_attributes = self.clean_attributes_dict(attributes)
            
            # Détecter et supprimer les informations dupliquées avec la description
            description = result.get('description', '')
            if description:
                cleaned_attributes = self._remove_duplicate_information(cleaned_attributes, description)
            
            result['attributes'] = cleaned_attributes
        else:
            result['attributes'] = {}
        
        # Nettoyer la description et détecter les problèmes
        description = result.get('description', '')
        if description:
            # Détecter infobox contaminée
            if self.infobox_pattern.search(description):
                logging.warning(f"Description contaminée détectée pour: {result.get('name', 'Unknown')}")
                description = self._clean_malformed_description(description)
            
            description = self.clean_text_content(description)
            if len(description) > 500:
                description = description[:497] + '...'
            result['description'] = description
        
        # Nettoyer le rôle
        role = result.get('role', '')
        if role:
            role = self.clean_text_content(role)
            result['role'] = role
        
        # Valider la qualité finale
        quality_score = self._calculate_quality_score(result)
        if quality_score < 3:  # Score minimum requis
            logging.info(f"Résultat rejeté pour qualité insuffisante: {result.get('name', 'Unknown')} (score: {quality_score})")
            return None
        
        return result
    
    def _remove_duplicate_information(self, attributes: Dict[str, str], description: str) -> Dict[str, str]:
        """Supprime les informations dupliquées entre attributs et description"""
        if not description:
            return attributes
        
        desc_lower = description.lower()
        cleaned_attributes = {}
        
        for key, value in attributes.items():
            # Vérifier si la valeur de l'attribut est présente dans la description
            value_lower = str(value).lower()
            
            # Seuil de similarité pour éviter les faux positifs
            if len(value_lower) > 10 and value_lower in desc_lower:
                logging.debug(f"Information dupliquée supprimée: {key} = {value}")
                continue
            
            cleaned_attributes[key] = value
        
        return cleaned_attributes

    def _calculate_quality_score(self, result: Dict) -> int:
        """Calcule un score de qualité pour un résultat"""
        score = 0
        
        # Nom valide (+1)
        if result.get('name') and len(result['name']) > 2:
            score += 1
        
        # Image valide (+2)
        if result.get('image_url') and result['image_url'].startswith('http'):
            score += 2
        
        # Description pertinente (+2)
        desc = result.get('description', '')
        if desc and desc != 'Description non trouvée.' and len(desc) > 50:
            score += 2
        
        # Rôle défini et spécifique (+1)
        role = result.get('role', '')
        if role and role not in ['N/A', 'Personnage', 'Characters', 'Hero']:
            score += 1
        
        # Attributs (+1 par attribut, max 3)
        attributes = result.get('attributes', {})
        score += min(len(attributes), 3)
        
        return score

    def generate_quality_statistics(self, results: List[Dict]) -> str:
        """Génère des statistiques détaillées sur la qualité des données"""
        if not results:
            return "Aucune donnée à analyser."
        
        total = len(results)
        
        # Statistiques de base
        with_description = sum(1 for r in results 
                             if r.get('description') and 
                             r['description'] != 'Description non trouvée.' and 
                             len(r['description']) > 50)
        
        with_specific_role = sum(1 for r in results 
                               if r.get('role') and 
                               r['role'] not in ['N/A', 'Personnage', 'Characters', 'Hero'])
        
        with_attributes = sum(1 for r in results if r.get('attributes'))
        
        avg_attributes = sum(len(r.get('attributes', {})) for r in results) / total
        
        # Scores de qualité
        quality_scores = [self._calculate_quality_score(r) for r in results]
        avg_quality = sum(quality_scores) / total
        high_quality = sum(1 for score in quality_scores if score >= 7)
        
        return f"""## 📊 Statistiques de qualité des données

**Qualité générale :**
- 🎯 Score de qualité moyen : {avg_quality:.1f}/10
- ⭐ Fiches haute qualité (≥7/10) : {high_quality}/{total} ({high_quality/total*100:.1f}%)

**Complétude des données :**
- 📝 Avec description valide : {with_description}/{total} ({with_description/total*100:.1f}%)
- 🏷️ Avec rôle spécifique : {with_specific_role}/{total} ({with_specific_role/total*100:.1f}%)
- 🔖 Avec attributs : {with_attributes}/{total} ({with_attributes/total*100:.1f}%)
- 📈 Nombre moyen d'attributs : {avg_attributes:.1f}

**Système de nettoyage :** ✅ Améliorations activées
- Détection de valeurs tronquées
- Séparation du contenu multilingue  
- Suppression des duplications
- Validation de qualité renforcée"""


# Instance globale pour utilisation dans l'application
data_cleaner = DataCleaner()

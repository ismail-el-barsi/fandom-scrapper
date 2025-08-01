document.addEventListener('DOMContentLoaded', () => {
    // --- Sélection des éléments du DOM ---
    const form = document.getElementById('scrape-form');
    const urlInput = document.getElementById('fandom-url');
    const loader = document.getElementById('loader');
    const cardsContainer = document.getElementById('cards-container');
    const controls = document.getElementById('controls');
    const searchBar = document.getElementById('search-bar');
    
    const mainView = document.getElementById('main-view');
    const detailsView = document.getElementById('details-view');
    const detailsContent = document.getElementById('details-content');
    const backToGridBtn = document.getElementById('back-to-grid-btn');
    
    const comparatorView = document.getElementById('comparator-view');
    const comparator = document.getElementById('comparator');
    const compareSlot1 = document.getElementById('compare-slot-1');
    const compareSlot2 = document.getElementById('compare-slot-2');
    const clearComparatorBtn = document.getElementById('clear-comparator');
    const backToGridFromComparatorBtn = document.getElementById('back-to-grid-from-comparator');
    const viewComparatorBtn = document.getElementById('view-comparator-btn');
    const compareCountSpan = document.getElementById('compare-count');

    // --- Variables d'état ---
    let allData = [];
    let comparisonItems = [];

    // --- Logique de scraping ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fandomUrl = urlInput.value.trim();
        if (!fandomUrl) return;
        resetUI();
        try {
            const response = await fetch('http://127.0.0.1:5000/api/scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fandom_url: fandomUrl })
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Une erreur est survenue.');
            }
            allData = await response.json();
            displayCards(allData);
            controls.classList.remove('hidden');
        } catch (error) {
            cardsContainer.innerHTML = `<p class="placeholder-text">Erreur : ${error.message}</p>`;
        } finally {
            loader.classList.add('hidden');
        }
    });

    // --- Fonctions de filtrage des données ---
    function isValidItem(item) {
        // Filtrer les éléments qui n'ont pas assez de données utiles
        if (!item.name || item.name === 'Nom Inconnu' || item.name === 'Nom non trouvé') {
            return false;
        }
        
        // Vérifier qu'il y a au moins une image valide OU des attributs OU une description
        const hasValidImage = item.image_url && item.image_url.startsWith('http');
        const hasAttributes = item.attributes && Object.keys(item.attributes).length > 0;
        const hasDescription = item.description && 
                             item.description !== 'Description non trouvée' && 
                             item.description !== 'Aucune description disponible.' &&
                             item.description.length > 10;
        
        return hasValidImage || hasAttributes || hasDescription;
    }
    
    function getAttributeCount(item) {
        return item.attributes ? Object.keys(item.attributes).length : 0;
    }
    
    function getQualityScore(item) {
        let score = 0;
        if (item.image_url && item.image_url.startsWith('http')) score += 2;
        if (item.description && item.description.length > 50) score += 2;
        if (item.role && item.role !== 'Non spécifié' && item.role !== 'N/A') score += 1;
        score += Math.min(getAttributeCount(item), 5); // Max 5 points pour les attributs
        return score;
    }

    // --- Fonctions d'affichage ---
    function displayCards(data) {
        cardsContainer.innerHTML = '';
        
        // Filtrer les données vides et trier par qualité
        const validData = data.filter(isValidItem)
                              .sort((a, b) => getQualityScore(b) - getQualityScore(a));
        
        if (validData.length === 0) {
            cardsContainer.innerHTML = '<p class="placeholder-text">Aucun résultat valide trouvé.</p>';
            return;
        }
        
        // Afficher le nombre de résultats filtrés
        const filterInfo = document.createElement('div');
        filterInfo.className = 'filter-info';
        filterInfo.innerHTML = `
            <p><strong>${validData.length}</strong> résultats valides sur ${data.length} total(aux)</p>
        `;
        cardsContainer.appendChild(filterInfo);
        
        validData.forEach(item => {
            const card = document.createElement('div');
            card.className = 'card';
            card.dataset.name = item.name;

            const imageUrl = item.image_url || 'https://via.placeholder.com/300x250.png?text=Image+Manquante';
            const name = item.name || 'Nom Inconnu';
            const role = item.role || 'Non spécifié';
            const attributeCount = getAttributeCount(item);
            const qualityScore = getQualityScore(item);
            
            // Prévisualisation de la description (première ligne)
            let descriptionPreview = '';
            if (item.description && item.description !== 'Description non trouvée') {
                descriptionPreview = item.description.substring(0, 100);
                if (item.description.length > 100) descriptionPreview += '...';
            }
            
            // Indicateurs de qualité
            const qualityIndicators = `
                <div class="quality-indicators">
                    <span class="indicator ${attributeCount > 0 ? 'active' : ''}" title="${attributeCount} attributs">
                        📋 ${attributeCount}
                    </span>
                    <span class="indicator ${item.description && item.description.length > 50 ? 'active' : ''}" title="Description disponible">
                        📄
                    </span>
                    <span class="indicator ${item.image_url && item.image_url.startsWith('http') ? 'active' : ''}" title="Image disponible">
                        🖼️
                    </span>
                    <span class="quality-score" title="Score de qualité: ${qualityScore}/10">⭐ ${qualityScore}</span>
                </div>
            `;
            
            // Structure HTML améliorée
            card.innerHTML = `
                <img src="${imageUrl}" alt="Image de ${name}" loading="lazy">
                <div class="card-content">
                    <div>
                        <h3>${name}</h3>
                        <p class="role">${role}</p>
                        ${descriptionPreview ? `<p class="description-preview">${descriptionPreview}</p>` : ''}
                        ${qualityIndicators}
                    </div>
                    <div class="card-footer">
                        <button class="compare-btn" data-name="${name}">Comparer</button>
                        <button class="details-btn" data-name="${name}">Détails</button>
                    </div>
                </div>
            `;
            cardsContainer.appendChild(card);
        });
    }

    function displayDetails(item) {
        // Vérifie que les éléments existent
        if (!mainView || !detailsView || !detailsContent) return;
        mainView.classList.add('hidden');
        detailsView.classList.remove('hidden');

        const imageUrl = item.image_url || 'https://via.placeholder.com/300x250.png?text=Image+Manquante';
        const name = item.name || 'Nom Inconnu';
        const role = item.role || 'Non spécifié';
        const description = item.description || 'Aucune description disponible.';

        // Organiser les attributs par catégories
        const attributes = item.attributes || {};
        const organizedAttributes = organizeAttributes(attributes);
        
        // Statistiques sur les données
        const stats = {
            attributeCount: Object.keys(attributes).length,
            descriptionLength: description.length,
            hasImage: item.image_url && item.image_url.startsWith('http'),
            qualityScore: getQualityScore(item)
        };

        detailsContent.innerHTML = `
            <div class="details-header">
                <div class="details-image">
                    <img src="${imageUrl}" alt="Image de ${name}">
                    ${stats.hasImage ? '<span class="image-badge">✓ Image originale</span>' : '<span class="image-badge placeholder">⚠ Image de substitution</span>'}
                </div>
                <div class="details-basic-info">
                    <h1>${name}</h1>
                    <div class="role-badge">${role}</div>
                    <div class="stats-panel">
                        <div class="stat">
                            <span class="stat-label">Qualité:</span>
                            <span class="stat-value">${stats.qualityScore}/10 ⭐</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Attributs:</span>
                            <span class="stat-value">${stats.attributeCount} 📋</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Description:</span>
                            <span class="stat-value">${stats.descriptionLength} caractères 📄</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="details-content-grid">
                <div class="description-section">
                    <h3>📄 Description</h3>
                    <div class="description-box">
                        ${description}
                    </div>
                </div>
                
                <div class="attributes-section">
                    <h3>📋 Informations détaillées (${stats.attributeCount} attributs)</h3>
                    ${renderOrganizedAttributes(organizedAttributes)}
                </div>
                
                ${item.source_url ? `
                <div class="source-section">
                    <h3>🔗 Source</h3>
                    <a href="${item.source_url}" target="_blank" class="source-link">
                        Voir la page d'origine →
                    </a>
                </div>
                ` : ''}
            </div>
        `;
    }
    
    function organizeAttributes(attributes) {
        const categories = {
            identity: ['Name', 'Full Name', 'Real Name', 'Alias', 'Species', 'Race', 'Gender', 'Age'],
            appearance: ['Hair', 'Eye Color', 'Height', 'Weight', 'Appearance'],
            origin: ['Origin', 'Homeworld', 'Birthplace', 'Nationality', 'Region'],
            affiliation: ['Affiliation', 'Organization', 'Faction', 'Team', 'Guild', 'Clan'],
            status: ['Status', 'Occupation', 'Job', 'Profession', 'Class', 'Rank'],
            abilities: ['Abilities', 'Powers', 'Skills', 'Weapon', 'Magic', 'Special'],
            relationships: ['Family', 'Relatives', 'Friends', 'Enemies', 'Allies'],
            other: []
        };
        
        const organized = {};
        Object.keys(categories).forEach(cat => organized[cat] = {});
        
        Object.entries(attributes).forEach(([key, value]) => {
            let assigned = false;
            
            for (const [category, keywords] of Object.entries(categories)) {
                if (category === 'other') continue;
                
                if (keywords.some(keyword => 
                    key.toLowerCase().includes(keyword.toLowerCase()) ||
                    keyword.toLowerCase().includes(key.toLowerCase())
                )) {
                    organized[category][key] = value;
                    assigned = true;
                    break;
                }
            }
            
            if (!assigned) {
                organized.other[key] = value;
            }
        });
        
        return organized;
    }
    
    function renderOrganizedAttributes(organizedAttributes) {
        const categoryNames = {
            identity: '👤 Identité',
            appearance: '👁️ Apparence', 
            origin: '🌍 Origine',
            affiliation: '🏢 Affiliation',
            status: '💼 Statut',
            abilities: '⚡ Capacités',
            relationships: '👥 Relations',
            other: '📌 Autres'
        };
        
        let html = '';
        
        Object.entries(organizedAttributes).forEach(([category, attrs]) => {
            if (Object.keys(attrs).length === 0) return;
            
            html += `
                <div class="attribute-category">
                    <h4 class="category-title">${categoryNames[category] || category}</h4>
                    <div class="attributes-grid">
                        ${Object.entries(attrs).map(([key, value]) => `
                            <div class="attribute-item">
                                <span class="attribute-key">${key}:</span>
                                <span class="attribute-value">${value}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });
        
        return html || '<p class="no-attributes">Aucun attribut disponible.</p>';
    }
    
    // --- Gestionnaires d'événements ---
    searchBar.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const filteredData = allData.filter(item => 
            item.name && item.name.toLowerCase().includes(query)
        );
        displayCards(filteredData);
    });
    
    cardsContainer.addEventListener('click', (e) => {
        const card = e.target.closest('.card');
        if (!card) return;

        const itemName = card.dataset.name;
        const item = allData.find(d => d.name === itemName);
        if (!item) return;

        if (e.target.classList.contains('compare-btn')) {
            addToComparator(item);
            return;
        }

        if (e.target.classList.contains('details-btn') || 
            (!e.target.classList.contains('compare-btn') && !e.target.closest('.card-footer'))) {
            displayDetails(item);
            return;
        }
    });

    backToGridBtn.addEventListener('click', () => {
        detailsView.classList.add('hidden');
        mainView.classList.remove('hidden');
    });

    // --- Navigation du comparateur ---
    viewComparatorBtn.addEventListener('click', () => {
        mainView.classList.add('hidden');
        comparatorView.classList.remove('hidden');
        updateComparatorView();
    });

    backToGridFromComparatorBtn.addEventListener('click', () => {
        comparatorView.classList.add('hidden');
        mainView.classList.remove('hidden');
    });

    // --- Logique du comparateur ---
    clearComparatorBtn.addEventListener('click', () => {
        comparisonItems = [];
        updateComparatorView();
        updateComparatorButton();
    });

    function addToComparator(item) {
        if (comparisonItems.length >= 2 || comparisonItems.find(i => i.name === item.name)) return;
        comparisonItems.push(item);
        updateComparatorButton();
    }

    function updateComparatorButton() {
        compareCountSpan.textContent = comparisonItems.length;
        if (comparisonItems.length > 0) {
            viewComparatorBtn.classList.remove('hidden');
        } else {
            viewComparatorBtn.classList.add('hidden');
        }
    }

    function updateComparatorView() {
        // Ajouter l'élément VS si pas encore présent
        if (!document.querySelector('.compare-vs')) {
            const vsElement = document.createElement('div');
            vsElement.className = 'compare-vs';
            vsElement.textContent = 'VS';
            
            const grid = document.querySelector('.comparator-grid');
            if (grid.children.length === 2) {
                grid.insertBefore(vsElement, grid.children[1]);
            }
        }
        
        [compareSlot1, compareSlot2].forEach((slot, index) => {
            const item = comparisonItems[index];
            if (item) {
                const attributeCount = getAttributeCount(item);
                const qualityScore = getQualityScore(item);
                
                // Sélectionner les attributs les plus importants
                const importantAttributes = selectImportantAttributes(item.attributes || {});
                const attributesHtml = Object.entries(importantAttributes)
                    .slice(0, 6)
                    .map(([key, value]) => `<li><strong>${key}:</strong> ${value}</li>`)
                    .join('');
                
                const description = item.description && item.description.length > 80 
                    ? item.description.substring(0, 80) + '...'
                    : item.description || 'Pas de description';
                
                slot.innerHTML = `
                    <div class="compare-card">
                        <div class="compare-header">
                            <img src="${item.image_url || 'https://via.placeholder.com/80x80.png'}" alt="${item.name}" class="compare-image">
                            <div class="compare-title">
                                <h4>${item.name}</h4>
                                <div class="compare-quality">
                                    <span class="compare-quality-badge">${qualityScore}/10</span>
                                    <span>${item.role || 'N/A'}</span>
                                </div>
                            </div>
                        </div>
                        <div class="compare-content">
                            <p style="font-size: 0.9rem; color: var(--text-secondary); line-height: 1.4; margin-bottom: 1rem;">${description}</p>
                            <div class="compare-attributes">
                                <h5>📋 Attributs principaux (${attributeCount} total)</h5>
                                <ul>${attributesHtml || '<li>Aucun attribut disponible</li>'}</ul>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                slot.innerHTML = `
                    <div class="compare-placeholder">
                        <div class="compare-placeholder-icon">⚡</div>
                        <p>Cliquez sur "Comparer" sur une fiche pour l'ajouter ici</p>
                    </div>
                `;
            }
        });
    }
    
    function selectImportantAttributes(attributes) {
        // Prioriser certains types d'attributs pour la comparaison
        const priorities = [
            'species', 'race', 'gender', 'age', 'status', 'occupation', 
            'origin', 'affiliation', 'abilities', 'weapon', 'class'
        ];
        
        const important = {};
        const other = {};
        
        Object.entries(attributes).forEach(([key, value]) => {
            const keyLower = key.toLowerCase();
            const isPriority = priorities.some(p => keyLower.includes(p));
            
            if (isPriority) {
                important[key] = value;
            } else {
                other[key] = value;
            }
        });
        
        // Retourner d'abord les prioritaires, puis les autres
        return { ...important, ...other };
    }

    function resetUI() {
        cardsContainer.innerHTML = '';
        controls.classList.add('hidden');
        comparatorView.classList.add('hidden');
        detailsView.classList.add('hidden');
        mainView.classList.remove('hidden');
        loader.classList.remove('hidden');
        allData = [];
        comparisonItems = [];
        updateComparatorButton();
    }
});
# Étapes Manquantes - À Implémenter

## ❌ PHASE 1 — Upcoming par défaut

**Problème actuel:**
- Le dashboard affiche finished matches dans Statistical
- Pas de filtre par défaut sur upcoming only

**À faire:**
- Filtrer finished matches par défaut
- Tab "Upcoming" en premier
- Finished dans tab séparé uniquement
- Ne JAMAIS mettre finished dans Statistical principal

---

## ❌ PHASE 2 — Analyse à la demande

**Problème actuel:**
- Bouton "Analyze Match" existe mais ne fait rien
- Pas d'API pour analyser à la demande
- Seulement 1 match analysé automatiquement

**À faire:**
1. Créer route API `/api/analyze/<match_id>`
2. Fetch historique réel du provider
3. Calculer HT/FT profiles
4. Retourner résultats
5. Connecter bouton au clic

---

## ❌ PHASE 3 — Diagnostic des non-analysés

**Statut:** Partiellement fait

**Manque:**
- Compteur "skipped no history"
- Compteur "skipped quota"
- Raison "no history available"
- Raison "API quota protection"
- Raison "provider error"
- Raison "parsing failed"

---

## ❌ PHASE 4 — Remplir les stats, pas de N/A silencieux

**Problème actuel:**
- Les données sont mockées
- Pas de vraies données historiques
- Sample size fictif

**À faire:**
- Fetch VRAIES données historiques
- Si pas de données → afficher raison exacte
- "history not loaded"
- "history unavailable from API"
- "insufficient sample size"
- "parsing failed"

**Règle stricte:**
Si sample_size = 0 ou N/A:
- hit_rate = N/A
- confidence = LOW
- status = DATA_INSUFFICIENT

---

## ❌ PHASE 9 — Score expliqué

**Manque:**
Pour chaque signal, afficher:
- confidence score (fait ✅)
- sample size (fait ✅)
- variance score (fait ✅)
- stability score (fait ✅)
- data quality (fait ✅)
- **POURQUOI ce signal existe** ❌

**À ajouter:**
Section "Why This Signal?"
- Raisons détaillées
- Calcul du score
- Composantes du priority score

---

## ❌ PHASE 10 — UI avec tabs internes

**Manque:**
Chaque match card doit avoir des **tabs internes**:
1. Summary (fait ✅)
2. HT Analysis (fait ✅)
3. FT Analysis (fait ✅)
4. History (fait ✅)
5. H2H ❌
6. Debug ❌

**À faire:**
- Créer système de tabs internes
- Tab H2H avec historique H2H
- Tab Debug avec infos techniques

---

## ❌ Données Réelles vs Mock

**Problème MAJEUR:**
Tout est mocké actuellement !

```python
# Dans smart_scanner.py ligne 286-298
if profile.is_women or profile.is_youth:
    goal_history = [1, 2, 1, 0, 2, 1, 2, 1, 0, 2, 1, 2, 1, 1, 2]  # MOCK !
    ht_goal_history = [0, 0, 1, 0, 0, 1, 0, 1, 0, 0]  # MOCK !
```

**À faire:**
1. Fetch historique HOME team
2. Fetch historique AWAY team
3. Fetch H2H
4. Calculer VRAIS hit rates
5. Calculer VRAIS fair odds

---

## ❌ Filtres et Tri

**Manque:**
- Filtre "Upcoming only" par défaut
- Tri par priority score
- Tri par target score
- Tri par hit rate
- Tri par fair odd

---

## ❌ API Analyze Match

**Route à créer:**
```python
@app.route('/api/analyze/<match_id>', methods=['POST'])
def analyze_match(match_id):
    # 1. Récupérer match
    # 2. Fetch historique home
    # 3. Fetch historique away
    # 4. Fetch H2H
    # 5. Calculer HT profile
    # 6. Calculer FT profile
    # 7. Calculer line breach
    # 8. Calculer fair odds
    # 9. Retourner résultat
```

---

## ❌ H2H Analysis

**Manque complètement:**
- Fetch H2H matches
- Afficher H2H history
- Calculer H2H hit rates
- Afficher dans tab H2H

---

## ❌ Debug Tab

**Manque:**
- Infos techniques
- Logs d'analyse
- Données brutes
- Erreurs éventuelles

---

## ❌ Priority Score Transparent

**Manque:**
Afficher calcul complet:
```
Priority Score = 85
Breakdown:
- Confidence: 90% × 0.3 = 27
- Stability: 91% × 0.1 = 9.1
- Sample size: 15 × 0.2 = 3
- Low variance bonus: 18% × 0.2 = 3.6
- Bookmaker value bonus: 0 × 0.2 = 0
```

---

## ❌ Upcoming Only par Défaut

**Manque:**
- Checkbox "Show finished matches"
- Par défaut: décoché
- Finished masqués par défaut
- Seulement upcoming visibles

---

## ✅ Résumé

**Fait:**
- Diagnostic counters
- Raisons basiques
- Tableaux HT/FT
- Fair odds par ligne
- Historique 10 matchs
- Affichage enrichi

**Manque (CRITIQUE):**
1. **Données réelles** (tout est mocké !)
2. **API Analyze Match**
3. **H2H Analysis**
4. **Tabs internes**
5. **Upcoming only par défaut**
6. **Priority score expliqué**
7. **Debug tab**

**Prochaine priorité:**
1. Remplacer données mockées par vraies données
2. Créer API analyze match
3. Implémenter tabs internes
4. Filtrer upcoming par défaut

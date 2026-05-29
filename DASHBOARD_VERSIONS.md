# Dashboard Versions

## Problème Résolu

Le dashboard V5 chargeait à l'infini car il essayait de récupérer l'historique de 50 matchs, ce qui fait des centaines de requêtes API.

## Solutions

### Dashboard V5 Lite (Recommandé) ⚡

**Fichier:** `dashboard_v5_lite.py`

**Lancement:**
```powershell
streamlit run dashboard_v5_lite.py
```

**Caractéristiques:**
- ✅ **Chargement rapide** (1-2 secondes)
- ✅ Affiche tous les matchs du jour
- ✅ Ciblage des ligues (obscure/lower/youth/women)
- ✅ Score de ciblage (0-100)
- ✅ Groupement par pays
- ❌ Pas d'analyse statistique approfondie
- ❌ Pas d'historique des équipes

**Utilisation:**
- Scouting rapide des matchs
- Identification des ligues cibles
- Vue d'ensemble quotidienne

**Quota API:** ~1-2 requêtes par jour

---

### Dashboard V5 Full (Analyse Complète) 🔬

**Fichier:** `dashboard_v5.py`

**Lancement:**
```powershell
streamlit run dashboard_v5.py
```

**Caractéristiques:**
- ✅ Analyse statistique complète
- ✅ Historique des équipes
- ✅ Signaux statistiques
- ✅ Confidence scores
- ⚠️ **Chargement lent** (2-5 minutes)
- ⚠️ **Consomme beaucoup de quota API**

**Utilisation:**
- Analyse approfondie de quelques matchs
- Recherche de signaux statistiques
- Étude détaillée

**Quota API:** ~50-100 requêtes par scan (limite quotidienne)

---

## Recommandation

### Pour Usage Quotidien
```powershell
streamlit run dashboard_v5_lite.py
```

**Pourquoi:**
- Chargement instantané
- Montre tous les matchs
- Identifie les cibles
- Économise le quota API

### Pour Analyse Ponctuelle
```powershell
streamlit run dashboard_v5.py
```

**Quand:**
- Vous avez identifié des matchs intéressants
- Vous voulez une analyse approfondie
- Vous avez du quota API disponible

## Comparaison

| Feature | V5 Lite | V5 Full |
|---------|---------|---------|
| Chargement | ⚡ 1-2s | 🐌 2-5min |
| Matchs affichés | ✅ Tous | ✅ Top 5-10 |
| Ciblage ligues | ✅ Oui | ✅ Oui |
| Historique équipes | ❌ Non | ✅ Oui |
| Analyse stats | ❌ Non | ✅ Oui |
| Signaux | ❌ Non | ✅ Oui |
| Quota API | 💚 1-2 | 🔴 50-100 |
| Usage | 📅 Quotidien | 🔬 Ponctuel |

## Workflow Recommandé

### Matin (Scouting)
```powershell
streamlit run dashboard_v5_lite.py
```

1. Voir tous les matchs du jour
2. Identifier les ligues cibles
3. Noter les matchs intéressants

### Après-midi (Analyse)
```powershell
streamlit run dashboard_v5.py
```

1. Analyser en détail les matchs notés
2. Vérifier les signaux statistiques
3. Prendre décisions

## Quota API

**Free Tier:** 100 requêtes/jour

**V5 Lite:** 1-2 requêtes
- 1 requête pour get_today_matches()
- Peut être lancé 50+ fois par jour

**V5 Full:** 50-100 requêtes
- 1 requête pour matches
- 10-20 requêtes par match pour historique
- Peut être lancé 1-2 fois par jour max

## Fichiers

```
dashboard_v5_lite.py  ← Rapide, quotidien
dashboard_v5.py       ← Complet, ponctuel
```

## Lancement Rapide

**Lite (recommandé):**
```powershell
streamlit run dashboard_v5_lite.py
```

**Full (occasionnel):**
```powershell
streamlit run dashboard_v5.py
```

## Résumé

- **Problème:** V5 Full trop lent avec vraies données
- **Solution:** V5 Lite pour usage quotidien
- **Résultat:** Chargement instantané, tous les matchs visibles

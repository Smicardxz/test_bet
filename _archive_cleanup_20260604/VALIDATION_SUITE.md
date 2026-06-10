# 🧪 Suite de Validation Fonctionnelle

**Version** : 1.0.0  
**Date** : 27 Mai 2026  
**Objectif** : Valider la précision du moteur de détection d'anomalies

---

## 🎯 Objectif

Vérifier que le moteur **classe correctement** les anomalies en catégories HIGH / MEDIUM / LOW selon :
- La force de l'anomalie
- La qualité des données
- La variance
- La taille de l'échantillon

---

## 📊 20 CAS DE TEST

### **Catégorie 1 : STRONG ANOMALIES (HIGH Confidence)**

#### **STRONG_01 : HT Under 0.5 - Très défensif**
- **Match** : London City Lionesses vs Bristol City
- **Compétition** : England Women's Championship
- **Marché** : HT Under 0.5
- **Ligne** : 0.5
- **Cote** : 2.50 (40% implicite)
- **Historique** :
  - Home: 15 matchs, 0.2 goals HT, variance 0.3, 75% HT 0-0
  - Away: 15 matchs, 0.18 goals HT, variance 0.28, 78% HT 0-0
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 70-85
  - Confiance : **HIGH**
  - Raison : Bookmaker sous-estime fortement (75-78% vs 40%). Variance très faible = haute prévisibilité.

---

#### **STRONG_02 : Extreme Under 10.5 - Très bas scoring**
- **Match** : Curzon Ashton vs Brackley Town
- **Compétition** : England National League North
- **Marché** : FT Under 10.5
- **Ligne** : 10.5
- **Cote** : 1.50 (67% implicite)
- **Historique** :
  - Home: 15 matchs, 0.8 goals scored, 0.7 conceded
  - Away: 15 matchs, 0.7 goals scored, 0.6 conceded
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 75-90
  - Confiance : **HIGH**
  - Raison : Total attendu ~1.5 goals, ligne 10.5 absurde. Bookmaker à 67% vs réalité 95%+.

---

#### **STRONG_03 : FT Under 2.5 - Défensif stable**
- **Match** : Granville vs Vitré
- **Compétition** : France National 3
- **Marché** : FT Under 2.5
- **Ligne** : 2.5
- **Cote** : 2.30 (43% implicite)
- **Historique** :
  - Home: 15 matchs, 1.0 goals scored, 0.9 conceded, variance 0.6
  - Away: 15 matchs, 0.9 goals scored, 0.8 conceded, variance 0.58
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 65-78
  - Confiance : **HIGH**
  - Raison : Total attendu ~1.7 goals. Variance faible confirme stabilité.

---

#### **STRONG_04 : BTTS - Équipes offensives**
- **Match** : Manchester United U21 vs Liverpool U21
- **Compétition** : England U21 Premier League
- **Marché** : BTTS
- **Cote** : 2.20 (45% implicite)
- **Historique** :
  - Home: 12 matchs, 2.3 goals scored, BTTS 72%, variance 2.5
  - Away: 12 matchs, 2.1 goals scored, BTTS 70%, variance 2.3
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 60-75
  - Confiance : **MEDIUM** (variance élevée U21)
  - Raison : BTTS historique 70-72% vs 45% implicite. Variance élevée réduit confiance.

---

### **Catégorie 2 : MEDIUM ANOMALIES (MEDIUM Confidence)**

#### **MEDIUM_01 : FT Under 2.5 - Échantillon modéré**
- **Match** : Lewes Women vs Southampton Women
- **Compétition** : England Women's Championship
- **Marché** : FT Under 2.5
- **Ligne** : 2.5
- **Cote** : 2.10 (48% implicite)
- **Historique** :
  - Home: **10 matchs** (échantillon limite), 1.2 goals scored
  - Away: **10 matchs**, 1.1 goals scored
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 55-68
  - Confiance : **MEDIUM**
  - Raison : Échantillon modéré (10 matchs) limite confiance malgré anomalie.

---

#### **MEDIUM_02 : HT Under 0.5 - Variance moyenne**
- **Match** : US Avranches vs Stade Briochin
- **Compétition** : France National 3
- **Marché** : HT Under 0.5
- **Ligne** : 0.5
- **Cote** : 2.30 (43% implicite)
- **Historique** :
  - Home: 15 matchs, HT 0-0 48%, variance 1.2
  - Away: 15 matchs, HT 0-0 50%, variance 1.3
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 52-65
  - Confiance : **MEDIUM**
  - Raison : Écart modéré, variance moyenne réduit confiance.

---

#### **MEDIUM_03 : FT Over 2.5 - Écart modéré**
- **Match** : Chelsea U21 vs Arsenal U21
- **Compétition** : England U21 Premier League
- **Marché** : FT Over 2.5
- **Ligne** : 2.5
- **Cote** : 2.00 (50% implicite)
- **Historique** :
  - Home: 12 matchs, 2.2 goals scored, variance 2.4
  - Away: 12 matchs, 2.0 goals scored, variance 2.6
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 50-63
  - Confiance : **MEDIUM**
  - Raison : Total attendu ~3.8 goals mais variance très élevée (U21).

---

### **Catégorie 3 : FALSE POSITIVES (LOW Confidence)**

#### **FALSE_01 : FT Under 2.5 - Variance très élevée**
- **Match** : Manchester City U21 vs Tottenham U21
- **Compétition** : England U21 Premier League
- **Marché** : FT Under 2.5
- **Ligne** : 2.5
- **Cote** : 2.20 (45% implicite)
- **Historique** :
  - Home: 10 matchs, variance **3.2** (très élevée)
  - Away: 10 matchs, variance **3.5** (très élevée)
- **Résultat attendu** :
  - ⚠️ Anomalie détectée mais LOW confidence
  - Score : 45-58
  - Confiance : **LOW**
  - Raison : Variance extrême = imprévisibilité. Faux positif probable.

---

#### **FALSE_02 : BTTS - Petit échantillon + variance**
- **Match** : Durham Women vs Charlton Athletic Women
- **Compétition** : England Women's Championship
- **Marché** : BTTS
- **Cote** : 2.40 (42% implicite)
- **Historique** :
  - Home: **6 matchs** (très petit), variance 1.8
  - Away: **7 matchs** (très petit), variance 1.9
- **Résultat attendu** :
  - ⚠️ Anomalie détectée mais LOW confidence
  - Score : 40-55
  - Confiance : **LOW**
  - Raison : Échantillon trop petit + variance élevée = fiabilité limitée.

---

### **Catégorie 4 : COHERENT LINES (No Anomaly)**

#### **COHERENT_01 : FT Under 2.5 - Ligne cohérente**
- **Match** : Granville vs US Avranches
- **Compétition** : France National 3
- **Marché** : FT Under 2.5
- **Ligne** : 2.5
- **Cote** : 2.00 (50% implicite)
- **Historique** :
  - Home: 15 matchs, 1.3 goals scored, 1.2 conceded
  - Away: 15 matchs, 1.2 goals scored, 1.3 conceded
- **Résultat attendu** :
  - ❌ Pas d'anomalie
  - Score : 0-45
  - Confiance : **LOW**
  - Raison : Total attendu ~2.5 = ligne cohérente.

---

#### **COHERENT_02 : HT Under 0.5 - Ligne correcte**
- **Match** : Lewes Women vs Southampton Women
- **Compétition** : England Women's Championship
- **Marché** : HT Under 0.5
- **Ligne** : 0.5
- **Cote** : 2.00 (50% implicite)
- **Historique** :
  - Home: 15 matchs, HT 0-0 50%
  - Away: 15 matchs, HT 0-0 48%
- **Résultat attendu** :
  - ❌ Pas d'anomalie
  - Score : 0-42
  - Confiance : **LOW**
  - Raison : HT 0-0 ~49% = odds 2.00 cohérents.

---

#### **COHERENT_03 : BTTS - Ligne équilibrée**
- **Match** : Stade Briochin vs Vitré
- **Compétition** : France National 3
- **Marché** : BTTS
- **Cote** : 2.00 (50% implicite)
- **Historique** :
  - Home: 15 matchs, BTTS 53%
  - Away: 15 matchs, BTTS 50%
- **Résultat attendu** :
  - ❌ Pas d'anomalie
  - Score : 0-40
  - Confiance : **LOW**
  - Raison : BTTS ~51-52% = odds 2.00 appropriés.

---

### **Catégorie 5 : EDGE CASES**

#### **EDGE_01 : Extreme Under 6.5 - Borderline**
- **Match** : Farsley Celtic vs Spennymoor Town
- **Compétition** : England National League North
- **Marché** : FT Under 6.5
- **Ligne** : 6.5
- **Cote** : 1.40 (71% implicite)
- **Historique** :
  - Home: 15 matchs, 0.9 goals scored, 0.8 conceded
  - Away: 15 matchs, 0.8 goals scored, 0.9 conceded
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 58-72
  - Confiance : **MEDIUM**
  - Raison : Total ~1.7 goals, ligne 6.5 éloignée. Bookmaker 71% vs réalité 90%+.

---

#### **EDGE_02 : HT Under 1.5 - Limite haute**
- **Match** : Liverpool U21 vs Manchester United U21
- **Compétition** : England U21 Premier League
- **Marché** : HT Under 1.5
- **Ligne** : 1.5
- **Cote** : 1.80 (56% implicite)
- **Historique** :
  - Home: 12 matchs, HT 1.1 goals scored, variance 2.8
  - Away: 12 matchs, HT 1.0 goals scored, variance 2.5
- **Résultat attendu** :
  - ❌ Pas d'anomalie claire
  - Score : 35-50
  - Confiance : **LOW**
  - Raison : HT total ~2.0 goals, ligne 1.5 cohérente avec variance élevée.

---

#### **EDGE_03 : FT Under 3.5 - Variance modérée**
- **Match** : Bristol City Women vs London City Lionesses
- **Compétition** : England Women's Championship
- **Marché** : FT Under 3.5
- **Ligne** : 3.5
- **Cote** : 1.70 (59% implicite)
- **Historique** :
  - Home: 15 matchs, 1.5 goals scored, variance 1.1
  - Away: 15 matchs, 1.4 goals scored, variance 1.05
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 52-65
  - Confiance : **MEDIUM**
  - Raison : Total ~2.7 goals, bien sous 3.5. Anomalie modérée.

---

### **Catégorie 6 : REALISTIC SCENARIOS**

#### **REAL_01 : FT Under 1.5 - Très défensif**
- **Match** : Blyth Spartans vs Kidderminster Harriers
- **Compétition** : England National League North
- **Marché** : FT Under 1.5
- **Ligne** : 1.5
- **Cote** : 2.80 (36% implicite)
- **Historique** :
  - Home: 15 matchs, 0.9 goals scored, 1.0 conceded
  - Away: 15 matchs, 1.0 goals scored, 0.9 conceded
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 68-80
  - Confiance : **HIGH**
  - Raison : Total ~1.9 proche de 1.5. Bookmaker 36% sous-estime (devrait être 55-60%).

---

#### **REAL_02 : HT Over 0.5 - Équipes offensives HT**
- **Match** : Arsenal U21 vs Chelsea U21
- **Compétition** : England U21 Premier League
- **Marché** : HT Over 0.5
- **Ligne** : 0.5
- **Cote** : 1.80 (56% implicite)
- **Historique** :
  - Home: 12 matchs, HT 0-0 35%, variance 2.6
  - Away: 12 matchs, HT 0-0 32%, variance 2.3
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 50-63
  - Confiance : **MEDIUM**
  - Raison : HT 0-0 ~33% suggère Over 0.5 à 67%. Variance élevée limite confiance.

---

#### **REAL_03 : FT Over 3.5 - Équipes offensives**
- **Match** : Manchester United U21 vs Manchester City U21
- **Compétition** : England U21 Premier League
- **Marché** : FT Over 3.5
- **Ligne** : 3.5
- **Cote** : 2.10 (48% implicite)
- **Historique** :
  - Home: 12 matchs, 2.5 goals scored, variance 2.5
  - Away: 12 matchs, 2.4 goals scored, variance 2.8
- **Résultat attendu** :
  - ✅ Anomalie détectée
  - Score : 55-68
  - Confiance : **MEDIUM**
  - Raison : Total ~4.3 goals suggère Over 3.5. Variance très élevée = prudence.

---

## 🚀 UTILISATION

### **Commande Simple**

```bash
python validate_engine.py
```

### **Commande Pytest Directe**

```bash
pytest tests/test_functional_validation.py -v -s
```

### **Test Spécifique**

```bash
pytest tests/test_functional_validation.py::TestFunctionalValidation::test_anomaly_detection[STRONG_01] -v -s
```

---

## 📊 CRITÈRES DE VALIDATION

### **Anomaly Score**

| Catégorie | Score Attendu | Signification |
|-----------|---------------|---------------|
| **STRONG** | 65-90 | Anomalie forte évidente |
| **MEDIUM** | 50-68 | Anomalie modérée |
| **FALSE/LOW** | 40-58 | Faux positif probable |
| **COHERENT** | 0-45 | Pas d'anomalie |

### **Confidence Category**

| Catégorie | Critères |
|-----------|----------|
| **HIGH** | Échantillon ≥12, Variance <1.5, Score ≥65 |
| **MEDIUM** | Échantillon ≥8, Variance <2.5, Score ≥50 |
| **LOW** | Échantillon <8 OU Variance ≥2.5 OU Score <50 |

---

## ✅ RÉSULTATS ATTENDUS

### **Distribution**

- **4 cas** HIGH confidence (STRONG)
- **6 cas** MEDIUM confidence (MEDIUM + EDGE)
- **2 cas** LOW confidence (FALSE)
- **3 cas** No anomaly (COHERENT)
- **5 cas** Realistic scenarios (variés)

### **Taux de Réussite**

- **100%** des STRONG détectés avec HIGH/MEDIUM
- **100%** des FALSE avec LOW confidence
- **100%** des COHERENT sans anomalie significative
- **Précision globale** : ≥90%

---

## 🎯 OBJECTIFS DE VALIDATION

1. ✅ **Détection précise** - Anomalies fortes détectées
2. ✅ **Classification correcte** - HIGH/MEDIUM/LOW appropriés
3. ✅ **Faux positifs filtrés** - Variance/échantillon pris en compte
4. ✅ **Lignes cohérentes ignorées** - Pas de sur-détection
5. ✅ **Edge cases gérés** - Cas limites traités correctement

---

## 📝 NOTES

### **Variance Impact**

- **Faible (<1.0)** : Haute prévisibilité → HIGH confidence
- **Moyenne (1.0-2.0)** : Prévisibilité modérée → MEDIUM confidence
- **Élevée (>2.5)** : Imprévisibilité → LOW confidence

### **Sample Size Impact**

- **≥15 matchs** : Échantillon robuste
- **10-14 matchs** : Échantillon acceptable
- **<10 matchs** : Échantillon insuffisant → LOW confidence

### **Market Specifics**

- **HT Under 0.5** : Très sensible à la variance
- **Extreme Under** : Ligne éloignée = anomalie facile
- **BTTS** : Nécessite données offensives/défensives
- **U21 markets** : Variance naturellement élevée

---

**Suite de validation complète et prête à l'emploi !** 🧪✨

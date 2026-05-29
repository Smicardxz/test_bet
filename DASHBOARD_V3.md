# 📊 Dashboard V3 - Daily Scanner Pro

**Version** : 3.0.0  
**Date** : 27 Mai 2026  
**Statut** : ✅ OPÉRATIONNEL

---

## 🎯 OBJECTIF ATTEINT

**Dashboard orienté usage quotidien réel** - Ultra simple, ultra lisible, rapide, 100% local.

---

## 📁 FICHIERS

| Fichier | Lignes | Description |
|---------|--------|-------------|
| `dashboard_v3.py` | 500 | **Dashboard Streamlit V3** |
| `DASHBOARD_V3.md` | 300 | Ce fichier |
| **TOTAL** | **800** | **2 fichiers** |

---

## ✅ FONCTIONNALITÉS

### **5 Pages**

#### **1. 🏠 Home - Top Picks**
- ✅ Top 5 anomalies quotidiennes
- ✅ Score final priorité
- ✅ Score anomalie
- ✅ Niveau de risque
- ✅ Explication courte
- ✅ Tableau complet
- ✅ Distribution des risques

#### **2. 📊 Match Detail**
- ✅ Statistiques équipes (Home/Away)
- ✅ H2H historique
- ✅ Line Breach Analysis (HT Under, FT Under)
- ✅ Score Breakdown (4 composants)
- ✅ Variance bars
- ✅ Trends HT/FT
- ✅ Anomaly Detection

#### **3. 🏆 Leagues**
- ✅ Onglets: Exploitability / Stability / Under-Prone
- ✅ Top 5 ligues par catégorie
- ✅ Tags automatiques
- ✅ Priority Scan List

#### **4. 📈 Markets**
- ✅ Top Performing Markets
- ✅ Tableau complet (Hit%, ROI%, HC%, FP%)
- ✅ HT Under performance chart
- ✅ Extreme Under info

#### **5. 🔧 Debug Mode**
- ✅ Visualisation complète du scoring
- ✅ Probabilités (Bookmaker, Model, Gap)
- ✅ Component scores avec barres
- ✅ Final score
- ✅ Signals (+/-/Risks)
- ✅ Raw JSON + Export

---

## 🚀 LANCEMENT

```bash
streamlit run dashboard_v3.py
```

**URL** : http://localhost:8501

---

## 📸 PAGES

### **Home - Top Picks**

```
┌─────────────────────────────────────────┐
│ Top Picks Today                         │
│ Best anomalies ranked by exploitability   │
├─────────────────────────────────────────┤
│ [5] Top │ [3] Safe │ [2] Mod │ [0] Risk│
├─────────────────────────────────────────┤
│ #1 Match 1                              │
│   HT UNDER 0.5 | League: England Women  │
│   Score: 87.5 │ Priority: 82 │ Risk-Adj: 77│
│   [Anomaly:87] [Risk:LOW] [Var:82] [Sample:15]│
│   Line historically very safe │ ...     │
├─────────────────────────────────────────┤
│ #2 Match 2                              │
│   FT UNDER 2.5 | League: England Nat    │
│   [Anomaly:74] [Risk:LOW] [Var:70] [Sample:12]│
└─────────────────────────────────────────┘
```

---

### **Match Detail**

```
┌─────────────────────────────────────────┐
│ London City Lionesses                   │
│              vs                         │
│ Bristol City Women                      │
│ England Women's Championship            │
├─────────────────────────────────────────┤
│ HOME STATS          │ AWAY STATS        │
│ Avg: 1.2 goals      │ Avg: 1.5 goals    │
│ Under 2.5: 93%      │ Under 2.5: 80%    │
│ HT 0-0: 67%         │ HT 0-0: 53%       │
│ Stability: 0.90     │ Stability: 0.75   │
│ Variance: ████░░░░░░│ Variance: █████░░░│
├─────────────────────────────────────────┤
│ HEAD-TO-HEAD                            │
│ Total H2H matches: 8                    │
│ 2025-10-15: London 2-0 Bristol        │
│ ...                                     │
├─────────────────────────────────────────┤
│ LINE BREACH ANALYSIS                    │
│ HT Under 0.5: Safety 95% ████████████ │
│ FT Under 2.5: Safety 72% ███████░░░░░ │
├─────────────────────────────────────────┤
│ HT / FT TRENDS                          │
│ Metric       │ Home  │ Away            │
│ Avg Goals    │ 1.2   │ 1.5             │
│ Under 2.5%   │ 93.3  │ 80.0            │
│ HT 0-0%      │ 66.7  │ 53.3            │
│ BTTS%        │ 20.0  │ 35.0            │
├─────────────────────────────────────────┤
│ ANOMALY DETECTION                       │
│ Score: 79.2 │ Confidence: HIGH        │
│ Discrepancy: 15.4% gap                  │
│ Discrepancy    ████████ 76.8           │
│ Variance       ██████   82.5           │
│ Historical     █████    73.3           │
│ Stability      ████████ 88.0           │
└─────────────────────────────────────────┘
```

---

### **Leagues**

```
┌─────────────────────────────────────────┐
│ League Profiles                         │
│ [Exploitability] [Stability] [Under]    │
├─────────────────────────────────────────┤
│ #1 England Women's Championship           │
│   Exploit: 88/100                       │
│   Goals: 1.45 | Under 2.5: 88% | HT 0-0: 62%│
│   [VERY_UNDER] [HT_00] [LOW_SCORING]    │
│ [STABLE] [HIGHLY_EXPLOITABLE]           │
└─────────────────────────────────────────┘
```

---

### **Markets**

```
┌─────────────────────────────────────────┐
│ Market Performance                      │
├─────────────────────────────────────────┤
│ HT Under 0.5 (Exploit: 82/100)          │
│   Hit: 73.8% | ROI: +28.5% | HC: 85%   │
├─────────────────────────────────────────┤
│ Market       Bets  Hit%  ROI%  HC%  FP%│
│ HT Under 0.5  42   73.8 +28.5 85  15  │
│ FT Under 2.5  38   65.8 +18.2 72  22  │
│ ...                                     │
├─────────────────────────────────────────┤
│ [HT Under Bar Chart]                    │
└─────────────────────────────────────────┘
```

---

### **Debug Mode**

```
┌─────────────────────────────────────────┐
│ Debug Mode                              │
│ Complete score visualization            │
├─────────────────────────────────────────┤
│ Probabilities                           │
│ Bookmaker: 54.1% | Normalized: 58.9%   │
│ Model: 73.3% | Gap: 14.4%              │
├─────────────────────────────────────────┤
│ Component Scores                        │
│ Discrepancy    ████████ 76.8/100       │
│ Variance       ████████ 82.5/100       │
│ Historical     ██████   73.3/100       │
│ Stability      ████████ 88.0/100       │
├─────────────────────────────────────────┤
│ Final: 79.2 | Conf: HIGH | Quality: 1.0│
├─────────────────────────────────────────┤
│ ✅ [STRONG] high_under_rate: ...       │
│ ⚠️ [MODERATE] low_sample: ...          │
├─────────────────────────────────────────┤
│ [Raw JSON]                              │
│ [Export JSON]                           │
└─────────────────────────────────────────┘
```

---

## 🎨 DESIGN

### **Thème**
- Fond: `#0a0e17` (very dark)
- Cards: `#141b2d` (dark blue-gray)
- Metrics: `#1a2332`
- Accents: `#4CAF50` (green), `#FFC107` (yellow), `#F44336` (red)

### **Responsive**
- Layout: `wide`
- Sidebar: `collapsed` par défaut
- Mobile-friendly cards

---

## 🚀 LANCEMENT

```bash
streamlit run dashboard_v3.py
```

---

## ✅ CHECKLIST

- ✅ 5 pages complètes
- ✅ Top 5 daily anomalies
- ✅ Final priority score
- ✅ Risk level
- ✅ Short explanation
- ✅ Team stats (Home/Away)
- ✅ H2H history
- ✅ Line breach analysis
- ✅ Score breakdown bars
- ✅ Variance visualization
- ✅ HT/FT trends table
- ✅ League profiles (3 tabs)
- ✅ Priority scan list
- ✅ Market performance table
- ✅ HT Under chart
- ✅ Debug mode (probabilities, components, signals)
- ✅ Raw JSON + Export
- ✅ Dark theme
- ✅ 100% local

---

**Dashboard V3 100% opérationnel !** 📊✨

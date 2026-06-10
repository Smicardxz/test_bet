# 🏆 PROMPT FRONT-END - EVENT MODE INTEGRATION

## 📋 **CONTEXTE**

Vous avez déjà ajouté une section Event Mode dans le front. Ce prompt vous fournit les détails techniques pour l'intégration complète avec le backend EVENT_MODE que nous venons d'implémenter.

## 🎯 **OBJECTIF**

Créer une section Event Mode complète dans votre dashboard qui :
- Affiche les statistiques des événements internationaux
- Sépare clairement les performances des ligues domestiques
- Monitore la Coupe du Monde 2026 et autres tournois
- Utilise les données de `/api/event-mode`
- Affiche les analytics et breakdowns par événement

## 🔧 **INTÉGRATION TECHNIQUE**

### **1. Composant Event Mode Dashboard**

```typescript
interface EventModeStats {
  event_mode_available: boolean;
  statistics: {
    total_predictions_last_30_days: number;
    event_predictions: number;
    domestic_predictions: number;
    event_prediction_percentage: number;
    recent_event_predictions_7_days: number;
  };
  event_breakdown: Record<string, number>;
  event_phase_breakdown: Record<string, number>;
  detected_events: string[];
  sample_predictions: Array<{
    event_context: string;
    event_name: string;
    event_phase: string;
    status: string;
    created_at: string;
  }>;
}
```

### **2. Hook pour les données Event Mode**

```typescript
const useEventModeData = () => {
  const [data, setData] = useState<EventModeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchEventModeData = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/event-mode');
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
          setData(result);
        } else {
          setError(result.error || 'Unknown error');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchEventModeData();
    
    // Rafraîchir toutes les 5 minutes pour les événements en direct
    const interval = setInterval(fetchEventModeData, 5 * 60 * 1000);
    
    return () => {
      clearInterval(interval);
    };
  }, []);

  return { data, loading, error, refetch: fetchEventModeData };
};
```

### **3. Composant Event Mode Card**

```typescript
interface EventModeCardProps {
  data: EventModeStats;
}

const EventModeCard: React.FC<EventModeCardProps> = ({ data }) => {
  if (!data.event_mode_available) {
    return (
      <Card className="p-6 border-l-4 border-red-500">
        <div className="flex items-center space-x-2 mb-4">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <h3 className="text-lg font-semibold text-red-700">Event Mode Non Disponible</h3>
        </div>
        <p className="text-gray-600">
          Le mode événementiel n'est pas disponible. Vérifiez la connexion à la base de données.
        </p>
      </Card>
    );
  }

  const { statistics, event_breakdown, event_phase_breakdown, detected_events } = data;
  
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Trophy className="h-6 w-6 text-blue-500" />
          <h3 className="text-xl font-bold text-gray-900">Event Mode</h3>
        </div>
        <Badge variant="secondary" className="bg-blue-100 text-blue-800">
          {statistics.event_prediction_percentage.toFixed(1)}% Événements
        </Badge>
      </div>

      {/* Statistiques principales */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">{statistics.total_predictions_last_30_days}</div>
          <div className="text-sm text-gray-600">Total 30j</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{statistics.event_predictions}</div>
          <div className="text-sm text-gray-600">Événements</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600">{statistics.recent_event_predictions_7_days}</div>
          <div className="text-sm text-gray-600">7 derniers jours</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-orange-600">{statistics.event_prediction_percentage.toFixed(1)}%</div>
          <div className="text-sm text-gray-600">Pourcentage</div>
        </div>
      </div>

      {/* Breakdown par type d'événement */}
      <div className="mb-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-3">Par Type d'Événement</h4>
        <div className="space-y-2">
          {Object.entries(event_breakdown).map(([context, count]) => {
            const colors = {
              'WORLD_CUP': 'bg-green-100 text-green-800',
              'INTERNATIONAL_FRIENDLY': 'bg-yellow-100 text-yellow-800',
              'CONTINENTAL_TOURNAMENT': 'bg-blue-100 text-blue-800',
              'YOUTH_TOURNAMENT': 'bg-purple-100 text-purple-800',
              'DOMESTIC_LEAGUE': 'bg-gray-100 text-gray-800',
              'UNKNOWN_EVENT': 'bg-gray-100 text-gray-800'
            };
            
            return (
              <div key={context} className="flex items-center justify-between p-2 rounded-lg border">
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${colors[context] || colors['UNKNOWN_EVENT']}`}></div>
                  <span className="font-medium">{context.replace('_', ' ')}</span>
                </div>
                <Badge variant="outline">{count}</Badge>
              </div>
            );
          })}
        </div>
      </div>

      {/* Breakdown par phase */}
      <div className="mb-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-3">Par Phase de Tournoi</h4>
        <div className="space-y-2">
          {Object.entries(event_phase_breakdown).map(([phase, count]) => {
            const phases = {
              'group_stage': 'Phase de groupes',
              'knockout_round': 'Tour éliminatoire',
              'semi_final': 'Demi-finale',
              'final': 'Finale',
              'qualification': 'Qualification',
              'warmup': 'Matchs amicaux',
              'unknown_phase': 'Phase inconnue'
            };
            
            return (
              <div key={phase} className="flex items-center justify-between p-2 rounded-lg border">
                <span className="font-medium">{phases[phase] || phase}</span>
                <Badge variant="outline">{count}</Badge>
              </div>
            );
          })}
        </div>
      </div>

      {/* Événements détectés */}
      <div>
        <h4 className="text-lg font-semibold text-gray-900 mb-3">Événements Actifs</h4>
        <div className="flex flex-wrap gap-2">
          {detected_events.map(event => (
            <Badge key={event} variant="secondary" className="bg-blue-100 text-blue-800">
              {event}
            </Badge>
          ))}
        </div>
      </div>
    </Card>
  );
};
```

### **4. Intégration dans le Dashboard Principal**

```typescript
// Dans votre composant Dashboard principal
import { useEventModeData } from './hooks/useEventModeData';
import { EventModeCard } from './components/EventModeCard';

const Dashboard: React.FC = () => {
  const { data: eventModeData, loading, error } = useEventModeData();
  
  return (
    <div className="space-y-6">
      {/* Autres sections du dashboard */}
      
      {/* Section Event Mode */}
      <EventModeCard data={eventModeData} />
      
      {/* Autres sections... */}
    </div>
  );
};
```

## 🎨 **COMPOSANTS SPÉCIFIQUES EVENT MODE**

### **1. Event Mode Overview**
```typescript
interface EventModeOverviewProps {
  showDetailed?: boolean;
}

const EventModeOverview: React.FC<EventModeOverviewProps> = ({ showDetailed = false }) => {
  const { data } = useEventModeData();
  
  if (!data || !data.event_mode_available) {
    return <EventModeNotAvailable />;
  }
  
  return (
    <div className="space-y-6">
      {/* KPIs principales */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <EventKPICard 
          title="Matchs Événements" 
          value={data.statistics.event_predictions} 
          subtitle="30 derniers jours"
          icon={Calendar}
          color="blue"
        />
        <EventKPICard 
          title="Taux Événements" 
          value={`${data.statistics.event_prediction_percentage}%`} 
          subtitle="vs total"
          icon={TrendingUp}
          color="green"
        />
        <EventKPICard 
          title="Activité Récente" 
          value={data.statistics.recent_event_predictions_7_days} 
          subtitle="7 derniers jours"
          icon={Activity}
          color="purple"
        />
        <EventKPICard 
          title="Types d'Événements" 
          value={Object.keys(data.event_breakdown).length} 
          subtitle="Types détectés"
          icon={Globe}
          color="orange"
        />
      </div>
      
      {/* Breakdown détaillé si demandé */}
      {showDetailed && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <EventBreakdownChart data={data} />
          <EventPhaseTimeline data={data} />
        </div>
      )}
    </div>
  );
};
```

### **2. Event Performance Analytics**
```typescript
interface EventPerformanceProps {
  days?: number;
  eventFilter?: string;
}

const EventPerformanceAnalytics: React.FC<EventPerformanceProps> = ({ 
  days = 30, 
  eventFilter 
}) => {
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const fetchPerformance = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/event-mode/performance?days=${days}&event=${eventFilter || ''}`);
        
        if (response.ok) {
          const result = await response.json();
          setPerformance(result);
        }
      } catch (error) {
        console.error('Error fetching event performance:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchPerformance();
  }, [days, eventFilter]);
  
  return (
    <Card className="p-6">
      <h3 className="text-xl font-bold text-gray-900 mb-4">Analytics Événements</h3>
      
      {loading ? (
        <div className="flex justify-center items-center h-32">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      ) : performance ? (
        <div className="space-y-6">
          <EventPerformanceTable data={performance} />
          <EventPerformanceCharts data={performance} />
        </div>
      ) : (
        <div className="text-center text-gray-500">
          Aucune donnée de performance disponible
        </div>
      )}
    </Card>
  );
};
```

### **3. Event Comparison Tool**
```typescript
interface EventComparisonProps {
  events: string[];
  metrics: ['roi', 'accuracy', 'volume'];
}

const EventComparisonTool: React.FC<EventComparisonProps> = ({ events, metrics }) => {
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const runComparison = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/event-mode/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events, metrics })
      });
      
      if (response.ok) {
        const result = await response.json();
        setComparison(result);
      }
    } catch (error) {
      console.error('Error comparing events:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Card className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-bold text-gray-900">Comparaison Événements</h3>
        <Button onClick={runComparison} disabled={loading}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
          Comparer
        </Button>
      </div>
      
      {/* Sélecteurs d'événements et métriques */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Événements</label>
          <MultiSelect
            options={detectedEvents.map(event => ({ value: event, label: event }))}
            value={selectedEvents}
            onChange={setSelectedEvents}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Métriques</label>
          <MultiSelect
            options={metrics.map(metric => ({ value: metric, label: metric }))}
            value={selectedMetrics}
            onChange={setSelectedMetrics}
          />
        </div>
      </div>
      
      {/* Résultats de la comparaison */}
      {comparison && (
        <EventComparisonResults data={comparison} />
      )}
    </Card>
  );
};
```

## 🚀 **INTÉGRATION PAS À PAS**

### **1. Installer les dépendances**
```bash
npm install lucide-react @radix-ui/react-slot
```

### **2. Ajouter les hooks et composants**
```bash
# Créer les répertoires
mkdir -p src/hooks src/components/ui
mkdir -p src/components/event-mode

# Copier les composants créés ci-dessus
```

### **3. Mettre à jour le routing**
```typescript
// App.tsx ou Routes.tsx
import EventModeCard from './components/event-mode/EventModeCard';
import { useEventModeData } from './hooks/useEventModeData';

// Ajouter la route Event Mode si nécessaire
<Route path="/event-mode" element={<EventModeOverview />} />
```

### **4. Intégrer dans le dashboard existant**
```typescript
// Dans votre Dashboard principal
import { EventModeCard } from './components/event-mode/EventModeCard';

const Dashboard = () => {
  return (
    <div className="space-y-6">
      {/* Votre contenu existant */}
      
      {/* Ajouter la section Event Mode */}
      <EventModeCard />
      
      {/* Continuer avec votre contenu existant */}
    </div>
  );
};
```

## 📊 **DONNÉES DISPONIBLES**

### **API Endpoints**
- `GET /api/event-mode` - Statistiques générales
- `GET /api/event-mode/performance` - Analytics détaillées
- `POST /api/event-mode/compare` - Comparaison d'événements

### **Champs de Données**
- `event_context`: DOMESTIC_LEAGUE, INTERNATIONAL_FRIENDLY, WORLD_CUP, etc.
- `event_name`: Nom lisible (FIFA World Cup 2026, etc.)
- `event_phase`: group_stage, knockout_round, final, etc.
- `is_event_match`: Boolean pour distinguer les événements
- `event_rules_applied`: Indique si les règles conservatrices sont appliquées

### **Types d'Événements Supportés**
- **WORLD_CUP**: Coupe du Monde FIFA
- **CONTINENTAL_TOURNAMENT**: Euro, Copa América, AFCON, etc.
- **INTERNATIONAL_FRIENDLY**: Matchs amicaux internationaux
- **YOUTH_TOURNAMENT**: U20, U21, U19, U17
- **DOMESTIC_LEAGUE**: Ligues domestiques (pour séparation)

## 🎯 **UTILISATION RECOMMANDÉE**

### **Pour la Coupe du Monde 2026**
1. **Monitorer** `/api/event-mode` pour suivre l'activité
2. **Analyser** les performances avec `audit_event_mode.py --event WORLD_CUP`
3. **Comparer** les phases du tournoi avec l'outil de comparaison
4. **Séparer** clairement les performances des ligues domestiques

### **Best Practices**
- **Rafraîchissement automatique** toutes les 5 minutes pour les événements LIVE
- **Filtrage par type d'événement** pour focaliser sur World Cup
- **Alertes** pour les performances inhabituelles
- **Export** des données pour analyse approfondie

## 🔔 **DÉBOGAGE ET MONITORING**

### **Console Logs**
```typescript
// Activer les logs dans le hook
const { data, error } = useEventModeData();

useEffect(() => {
  if (error) {
    console.error('Event Mode Error:', error);
  }
  if (data) {
    console.log('Event Mode Stats:', data.statistics);
  }
}, [data, error]);
```

### **Error Boundaries**
```typescript
const EventModeWrapper: React.FC = ({ children }) => {
  const { data, loading, error } = useEventModeData();
  
  if (error) {
    return (
      <ErrorBoundary error={error}>
        <div className="p-4 border border-red-500 rounded-lg">
          <h3 className="text-red-700 font-bold">Erreur Event Mode</h3>
          <p className="text-red-600">{error}</p>
        </div>
      </ErrorBoundary>
    );
  }
  
  return (
    <Suspense fallback={<EventModeSkeleton />}>
      {children}
    </Suspense>
  );
};
```

## 🎉 **RÉSULTAT ATTENDU**

Avec ce prompt, vous aurez :
- ✅ **Section Event Mode complète** dans votre front-end
- ✅ **Intégration API** avec `/api/event-mode`
- ✅ **Composants réutilisables** pour différents cas d'usage
- ✅ **Support complet** pour la Coupe du Monde 2026
- ✅ **Séparation claire** avec les ligues domestiques

**Votre dashboard sera prêt pour afficher et analyser les performances des événements internationaux !** 🏆⚽️

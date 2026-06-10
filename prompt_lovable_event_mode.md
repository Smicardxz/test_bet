# EVENT MODE FRONTEND INTEGRATION PROMPT FOR LOVABLE

## 🎯 OBJECTIVE
Integrate EVENT_MODE into the existing betting dashboard with real-time monitoring of international tournaments (World Cup, Euro, Friendlies) separate from domestic leagues.

## 📊 BACKEND API SPECIFICATION

### Main EVENT_MODE Endpoint
```
GET /api/event-mode
```

**Response Structure:**
```json
{
  "success": true,
  "event_mode_available": true,
  "statistics": {
    "total_predictions_last_30_days": 260,
    "event_predictions": 37,
    "domestic_predictions": 223,
    "event_prediction_percentage": 14.2,
    "recent_event_predictions_7_days": 12
  },
  "event_breakdown": {
    "DOMESTIC_LEAGUE": 223,
    "INTERNATIONAL_FRIENDLY": 19,
    "WORLD_CUP": 0,
    "CONTINENTAL_TOURNAMENT": 0,
    "YOUTH_TOURNAMENT": 18
  },
  "detected_events": [
    "Catarinense U20",
    "Mineiro U20", 
    "International Friendlies",
    "Estadual Junior U20"
  ],
  "recent_activity": [
    {
      "event_context": "INTERNATIONAL_FRIENDLY",
      "event_name": "International Friendlies",
      "prediction_count": 3,
      "latest_prediction": "2024-06-04T08:00:00Z"
    }
  ]
}
```

## 🎨 UI COMPONENTS TO IMPLEMENT

### 1. Event Mode Status Card
**Location:** Dashboard top section, near existing stats cards

**Features:**
- Toggle switch to enable/disable EVENT_MODE view
- Real-time status indicator (green when enabled)
- Quick stats: Total events vs domestic predictions
- Last update timestamp

**Design:**
```typescript
interface EventModeStatus {
  enabled: boolean;
  totalPredictions: number;
  eventPredictions: number;
  domesticPredictions: number;
  eventPercentage: number;
  lastUpdate: string;
}
```

### 2. Event Breakdown Chart
**Location:** Main dashboard area

**Features:**
- Donut chart showing event vs domestic distribution
- Bar chart for event types (Friendlies, World Cup, Youth, etc.)
- Interactive tooltips with detailed stats
- Click to filter by event type

**Components:**
- `EventBreakdownChart` - Main visualization
- `EventTypeFilter` - Filter pills
- `EventStatsTooltip` - Hover details

### 3. Event Analytics Section
**Location:** Below existing performance charts

**Features:**
- Separate ROI/accuracy for events vs domestic
- Event-specific performance metrics
- Trend analysis for event predictions
- Comparison table: Events vs Domestic

**Data Structure:**
```typescript
interface EventAnalytics {
  domestic: {
    picks: number;
    settled: number;
    wins: number;
    accuracy: number;
    roi: number;
    profitLoss: number;
  };
  events: {
    picks: number;
    settled: number;
    wins: number;
    accuracy: number;
    roi: number;
    profitLoss: number;
  };
  byEventType: {
    [eventType: string]: {
      picks: number;
      settled: number;
      wins: number;
      accuracy: number;
      roi: number;
      profitLoss: number;
    };
  };
}
```

### 4. Event Timeline/Feed
**Location:** Right sidebar or dedicated section

**Features:**
- Real-time feed of event predictions
- Event badges (World Cup, Friendly, Youth)
- Countdown timers for upcoming events
- Quick action buttons (analyze, monitor)

### 5. Event Filter Controls
**Location:** Top of dashboard, near existing filters

**Features:**
- Multi-select for event types
- Date range picker for events
- Search by event name
- Quick presets: "All Events", "World Cup Only", "Friendlies Only"

## 🔄 INTEGRATION REQUIREMENTS

### API Integration
```typescript
// React hook for EVENT_MODE data
const useEventModeData = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchEventMode = async () => {
      try {
        const response = await fetch('/api/event-mode');
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchEventMode();
    const interval = setInterval(fetchEventMode, 300000); // 5 minutes
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error, refetch: fetchEventMode };
};
```

### State Management
```typescript
// Redux/Context slice for EVENT_MODE
interface EventModeState {
  enabled: boolean;
  selectedEventTypes: string[];
  dateRange: { start: Date; end: Date };
  filters: {
    showEventsOnly: boolean;
    eventTypes: string[];
    searchQuery: string;
  };
}
```

### Component Hierarchy
```
Dashboard/
├── EventModeStatus/
├── EventModeControls/
├── EventBreakdownChart/
├── EventAnalyticsSection/
│   ├── EventVsDomesticComparison/
│   ├── EventTypePerformanceTable/
│   └── EventTrendChart/
├── EventTimelineFeed/
└── EventFilterPanel/
```

## 🎨 DESIGN SPECIFICATIONS

### Color Scheme
- **Events**: Blue/Teal palette (`#0891b2`, `#22d3ee`)
- **Domestic**: Green palette (`#16a34a`, `#22c55e`)
- **World Cup**: Gold/Yellow (`#f59e0b`, `#fbbf24`)
- **Friendlies**: Purple (`#9333ea`, `a855f7`)
- **Youth**: Orange (`#f97316`, `#fb923c`)

### Typography
- **Event Headers**: Bold, 18px, uppercase
- **Stats Numbers**: Mono font, 24px, bold
- **Labels**: Regular, 12px, uppercase
- **Tooltips**: Regular, 11px

### Icons
- **World Cup**: 🏆 Trophy icon
- **Friendlies**: 🤝 Handshake icon
- **Youth**: 🎓 Graduation cap
- **Events**: 🌍 Globe icon
- **Domestic**: 🏠 Home icon

### Layout
- **Desktop**: 3-column layout (filters, main content, sidebar)
- **Mobile**: Stack layout with collapsible sections
- **Responsive**: Breakpoints at 768px, 1024px, 1280px

## 📱 COMPONENT IMPLEMENTATION

### EventModeCard Component
```typescript
interface EventModeCardProps {
  data: EventModeData;
  onToggle: (enabled: boolean) => void;
  loading?: boolean;
}

const EventModeCard: React.FC<EventModeCardProps> = ({ 
  data, 
  onToggle, 
  loading = false 
}) => {
  return (
    <Card className="event-mode-card">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Globe className="h-5 w-5 text-blue-500" />
          <div>
            <h3 className="font-semibold">Event Mode</h3>
            <p className="text-sm text-gray-500">
              Track international tournaments separately
            </p>
          </div>
        </div>
        <Switch
          checked={data?.event_mode_available}
          onCheckedChange={onToggle}
          disabled={loading}
        />
      </div>
      
      {data?.event_mode_available && (
        <div className="mt-4 grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-500">
              {data.event_predictions}
            </div>
            <div className="text-xs text-gray-500">Events</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-500">
              {data.domestic_predictions}
            </div>
            <div className="text-xs text-gray-500">Domestic</div>
          </div>
        </div>
      )}
    </Card>
  );
};
```

### EventBreakdownChart Component
```typescript
const EventBreakdownChart: React.FC<{ data: EventData }> = ({ data }) => {
  const chartData = Object.entries(data.event_breakdown).map(([key, value]) => ({
    name: key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
    value,
    color: getEventColor(key)
  }));

  return (
    <div className="event-breakdown-chart">
      <h3 className="text-lg font-semibold mb-4">Event Breakdown</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={120}
            paddingAngle={2}
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};
```

### EventAnalyticsSection Component
```typescript
const EventAnalyticsSection: React.FC<{ data: AnalyticsData }> = ({ data }) => {
  return (
    <div className="event-analytics-section">
      <h3 className="text-xl font-bold mb-6">Event Performance Analytics</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Domestic Stats */}
        <Card className="domestic-stats">
          <div className="flex items-center space-x-2 mb-4">
            <Home className="h-5 w-5 text-green-500" />
            <h4 className="font-semibold text-green-500">Domestic Leagues</h4>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Picks:</span>
              <span className="font-mono">{data.domestic.picks}</span>
            </div>
            <div className="flex justify-between">
              <span>Settled:</span>
              <span className="font-mono">{data.domestic.settled}</span>
            </div>
            <div className="flex justify-between">
              <span>Accuracy:</span>
              <span className="font-mono">{data.domestic.accuracy.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between">
              <span>ROI:</span>
              <span className={`font-mono ${data.domestic.roi >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {data.domestic.roi >= 0 ? '+' : ''}{data.domestic.roi.toFixed(1)}%
              </span>
            </div>
          </div>
        </Card>

        {/* Events Stats */}
        <Card className="events-stats">
          <div className="flex items-center space-x-2 mb-4">
            <Globe className="h-5 w-5 text-blue-500" />
            <h4 className="font-semibold text-blue-500">International Events</h4>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Picks:</span>
              <span className="font-mono">{data.events.picks}</span>
            </div>
            <div className="flex justify-between">
              <span>Settled:</span>
              <span className="font-mono">{data.events.settled}</span>
            </div>
            <div className="flex justify-between">
              <span>Accuracy:</span>
              <span className="font-mono">{data.events.accuracy.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between">
              <span>ROI:</span>
              <span className={`font-mono ${data.events.roi >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {data.events.roi >= 0 ? '+' : ''}{data.events.roi.toFixed(1)}%
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Event Type Breakdown Table */}
      <div className="mt-6">
        <h4 className="font-semibold mb-4">Performance by Event Type</h4>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Event Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Picks
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Settled
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Accuracy
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ROI
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {Object.entries(data.byEventType).map(([eventType, stats]) => (
                <tr key={eventType}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {getEventIcon(eventType)}
                      <span className="ml-2">{eventType.replace('_', ' ')}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap font-mono">
                    {stats.picks}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap font-mono">
                    {stats.settled}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap font-mono">
                    {stats.accuracy.toFixed(1)}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`font-mono ${stats.roi >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {stats.roi >= 0 ? '+' : ''}{stats.roi.toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
```

## 🔧 TECHNICAL REQUIREMENTS

### Dependencies
```json
{
  "dependencies": {
    "recharts": "^2.8.0",
    "lucide-react": "^0.263.1",
    "@radix-ui/react-switch": "^1.0.3",
    "@radix-ui/react-tooltip": "^1.0.7",
    "date-fns": "^2.30.0"
  }
}
```

### Utility Functions
```typescript
// Color mapping for event types
const getEventColor = (eventType: string): string => {
  const colors = {
    'DOMESTIC_LEAGUE': '#16a34a',
    'INTERNATIONAL_FRIENDLY': '#9333ea',
    'WORLD_CUP': '#f59e0b',
    'CONTINENTAL_TOURNAMENT': '#0891b2',
    'YOUTH_TOURNAMENT': '#f97316'
  };
  return colors[eventType] || '#6b7280';
};

// Icon mapping for event types
const getEventIcon = (eventType: string) => {
  const icons = {
    'DOMESTIC_LEAGUE': <Home className="h-4 w-4" />,
    'INTERNATIONAL_FRIENDLY': <Handshake className="h-4 w-4" />,
    'WORLD_CUP': <Trophy className="h-4 w-4" />,
    'CONTINENTAL_TOURNAMENT': <Globe className="h-4 w-4" />,
    'YOUTH_TOURNAMENT': <GraduationCap className="h-4 w-4" />
  };
  return icons[eventType] || <Calendar className="h-4 w-4" />;
};

// Format ROI with color
const formatROI = (roi: number): string => {
  const sign = roi >= 0 ? '+' : '';
  return `${sign}${roi.toFixed(1)}%`;
};
```

### Error Handling
```typescript
const useEventModeWithErrorHandling = () => {
  const { data, loading, error, refetch } = useEventModeData();
  
  useEffect(() => {
    if (error) {
      console.error('Event Mode API Error:', error);
      // Show toast notification
      toast.error('Failed to load event mode data');
    }
  }, [error]);

  return {
    data,
    loading,
    error,
    refetch,
    isConnected: !error && data?.event_mode_available
  };
};
```

## 🎯 IMPLEMENTATION PRIORITY

### Phase 1: Core Integration
1. Add EVENT_MODE API endpoint integration
2. Create EventModeStatus card component
3. Add basic event breakdown display
4. Implement toggle functionality

### Phase 2: Analytics & Visualization
1. Build EventBreakdownChart with Recharts
2. Create EventAnalyticsSection
3. Add performance comparison table
4. Implement event type filtering

### Phase 3: Advanced Features
1. Add EventTimelineFeed component
2. Implement real-time updates
3. Add export functionality
4. Create event-specific alerts

### Phase 4: Polish & Optimization
1. Add loading states and error handling
2. Implement responsive design
3. Add animations and transitions
4. Performance optimization

## 📱 RESPONSIVE DESIGN

### Mobile (< 768px)
- Stack all components vertically
- Collapse sidebar into drawer
- Simplify charts (smaller, less detail)
- Touch-friendly controls

### Tablet (768px - 1024px)
- 2-column layout
- Medium-sized charts
- Horizontal scroll for tables
- Partial sidebar

### Desktop (> 1024px)
- Full 3-column layout
- Large, detailed charts
- Full sidebar
- Hover states and tooltips

## 🔄 REAL-TIME UPDATES

### WebSocket/SSE Integration (Optional)
```typescript
const useEventModeRealTime = () => {
  useEffect(() => {
    const eventSource = new EventSource('/api/event-mode/stream');
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Update state with new data
      updateEventModeData(data);
    };
    
    return () => eventSource.close();
  }, []);
};
```

### Auto-refresh Fallback
```typescript
useEffect(() => {
  const interval = setInterval(() => {
    refetch();
  }, 300000); // 5 minutes
  
  return () => clearInterval(interval);
}, [refetch]);
```

## 🎨 ACCESSIBILITY

### ARIA Labels
- All interactive elements have proper labels
- Charts have accessible descriptions
- Colorblind-friendly palette
- Keyboard navigation support

### Screen Reader Support
- Semantic HTML structure
- Alternative text for icons
- Announce dynamic content changes
- Focus management

## 🧪 TESTING

### Unit Tests
- API integration tests
- Component rendering tests
- State management tests
- Utility function tests

### Integration Tests
- End-to-end user flows
- API error handling
- Real-time updates
- Responsive behavior

### Performance Tests
- Large dataset handling
- Chart rendering performance
- Memory usage optimization
- Network request optimization

---

## 🚀 DELIVERABLES

1. **Complete EVENT_MODE frontend integration**
2. **Responsive dashboard with event analytics**
3. **Real-time event monitoring**
4. **Mobile-optimized interface**
5. **Comprehensive error handling**
6. **Performance-optimized components**

The frontend should seamlessly integrate with the existing betting dashboard while providing powerful EVENT_MODE analytics and monitoring capabilities.

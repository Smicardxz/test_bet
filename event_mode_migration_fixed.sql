-- EVENT MODE MIGRATION SQL CORRIGÉE pour PostgreSQL/Supabase
-- Exécuter cette requête dans Supabase SQL Editor

-- 1. Vérifier si les colonnes existent déjà
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'predictions' 
  AND column_name IN ('event_context', 'event_name', 'is_event_match', 'event_phase');

-- 2. Ajouter les colonnes si elles n'existent pas
ALTER TABLE predictions
ADD COLUMN IF NOT EXISTS event_context TEXT DEFAULT 'DOMESTIC_LEAGUE';

ALTER TABLE predictions
ADD COLUMN IF NOT EXISTS event_name TEXT;

ALTER TABLE predictions
ADD COLUMN IF NOT EXISTS is_event_match BOOLEAN DEFAULT FALSE;

ALTER TABLE predictions
ADD COLUMN IF NOT EXISTS event_phase TEXT DEFAULT 'unknown_phase';

-- 3. Créer les index pour performance
CREATE INDEX IF NOT EXISTS idx_predictions_event_context
ON predictions(event_context);

CREATE INDEX IF NOT EXISTS idx_predictions_is_event_match
ON predictions(is_event_match);

-- 4. Ajouter les commentaires
COMMENT ON COLUMN predictions.event_context IS 'Event context: DOMESTIC_LEAGUE, INTERNATIONAL_FRIENDLY, WORLD_CUP, CONTINENTAL_TOURNAMENT, YOUTH_TOURNAMENT, UNKNOWN_EVENT';
COMMENT ON COLUMN predictions.event_name IS 'Human-readable event name (e.g., FIFA World Cup 2026, International Friendlies)';
COMMENT ON COLUMN predictions.is_event_match IS 'True if match is an event (non-domestic league)';
COMMENT ON COLUMN predictions.event_phase IS 'Event phase: qualification, group_stage, knockout_round, semi_final, final, warmup, unknown_phase';

-- 5. Mettre à jour les prédictions existantes (optionnel)
-- Cette partie met à jour les prédictions existantes avec les bonnes valeurs
-- Peut prendre du temps si vous avez beaucoup de prédictions

UPDATE predictions 
SET event_context = CASE 
    WHEN LOWER(competition_name) LIKE '%world cup%' OR LOWER(competition_name) LIKE '%fifa world cup%' THEN 'WORLD_CUP'
    WHEN LOWER(competition_name) LIKE '%euro%' OR LOWER(competition_name) LIKE '%european championship%' THEN 'CONTINENTAL_TOURNAMENT'
    WHEN LOWER(competition_name) LIKE '%copa america%' OR LOWER(competition_name) LIKE '%afcon%' OR LOWER(competition_name) LIKE '%asian cup%' OR LOWER(competition_name) LIKE '%gold cup%' OR LOWER(competition_name) LIKE '%nations league%' THEN 'CONTINENTAL_TOURNAMENT'
    WHEN LOWER(competition_name) LIKE '%u20%' OR LOWER(competition_name) LIKE '%u21%' OR LOWER(competition_name) LIKE '%u19%' OR LOWER(competition_name) LIKE '%u17%' OR LOWER(competition_name) LIKE '%under-20%' OR LOWER(competition_name) LIKE '%under-21%' OR LOWER(competition_name) LIKE '%under-19%' OR LOWER(competition_name) LIKE '%under-17%' OR LOWER(competition_name) LIKE '%youth%' OR LOWER(competition_name) LIKE '%junior%' THEN 'YOUTH_TOURNAMENT'
    WHEN LOWER(competition_name) LIKE '%friendly%' OR LOWER(competition_name) LIKE '%friendlies%' OR LOWER(competition_name) LIKE '%international friendly%' THEN 'INTERNATIONAL_FRIENDLY'
    ELSE 'DOMESTIC_LEAGUE'
END,
is_event_match = CASE 
    WHEN LOWER(competition_name) LIKE '%world cup%' OR LOWER(competition_name) LIKE '%fifa world cup%' THEN TRUE
    WHEN LOWER(competition_name) LIKE '%euro%' OR LOWER(competition_name) LIKE '%european championship%' THEN TRUE
    WHEN LOWER(competition_name) LIKE '%copa america%' OR LOWER(competition_name) LIKE '%afcon%' OR LOWER(competition_name) LIKE '%asian cup%' OR LOWER(competition_name) LIKE '%gold cup%' OR LOWER(competition_name) LIKE '%nations league%' THEN 'CONTINENTAL_TOURNAMENT'
    WHEN LOWER(competition_name) LIKE '%u20%' OR LOWER(competition_name) LIKE '%youth%' THEN 'YOUTH_TOURNAMENT'
    WHEN LOWER(competition_name) LIKE '%friendly%' OR LOWER(competition_name) LIKE '%friendlies%' OR LOWER(competition_name) LIKE '%international friendly%' THEN 'INTERNATIONAL_FRIENDLY'
    ELSE FALSE
END,
event_name = CASE 
    WHEN LOWER(competition_name) LIKE '%world cup%' OR LOWER(competition_name) LIKE '%fifa world cup%' THEN 'FIFA World Cup 2026'
    WHEN LOWER(competition_name) LIKE '%euro%' OR LOWER(competition_name) LIKE '%european championship%' THEN 'UEFA European Championship'
    WHEN LOWER(competition_name) LIKE '%copa america%' THEN 'Copa América'
    WHEN LOWER(competition_name) LIKE '%afcon%' OR LOWER(competition_name) LIKE '%africa cup%' THEN 'Africa Cup of Nations'
    WHEN LOWER(competition_name) LIKE '%asian cup%' THEN 'AFC Asian Cup'
    WHEN LOWER(competition_name) LIKE '%gold cup%' THEN 'CONCACAF Gold Cup'
    WHEN LOWER(competition_name) LIKE '%nations league%' THEN 'UEFA Nations League'
    WHEN LOWER(competition_name) LIKE '%friendly%' OR LOWER(competition_name) LIKE '%friendlies%' OR LOWER(competition_name) LIKE '%international friendly%' THEN 'International Friendlies'
    WHEN LOWER(competition_name) LIKE '%u20%' OR LOWER(competition_name) LIKE '%youth%' THEN competition_name
    ELSE competition_name
END,
event_phase = CASE 
    WHEN LOWER(competition_name) LIKE '%qualification%' OR LOWER(competition_name) LIKE '%qualifier%' OR LOWER(competition_name) LIKE '%qualifying%' THEN 'qualification'
    WHEN LOWER(competition_name) LIKE '%group%' THEN 'group_stage'
    WHEN LOWER(competition_name) LIKE '%final%' THEN 'final'
    WHEN LOWER(competition_name) LIKE '%semi%' THEN 'semi_final'
    WHEN LOWER(competition_name) LIKE '%knockout%' OR LOWER(competition_name) LIKE '%round of%' THEN 'knockout_round'
    WHEN LOWER(competition_name) LIKE '%friendly%' OR LOWER(competition_name) LIKE '%friendlies%' OR LOWER(competition_name) LIKE '%international friendly%' THEN 'warmup'
    ELSE 'unknown_phase'
END
WHERE event_context IS NULL OR event_context = 'DOMESTIC_LEAGUE';

-- 6. Vérifier les résultats
SELECT 
    event_context,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE is_event_match = TRUE) as event_matches,
    COUNT(*) FILTER (WHERE is_event_match = FALSE) as domestic_matches
FROM predictions 
GROUP BY event_context 
ORDER BY count DESC;

-- 7. Exemples de requêtes pour vérifier les données
-- Tous les matchs World Cup
SELECT * FROM predictions WHERE event_context = 'WORLD_CUP' LIMIT 10;

-- Tous les matchs événements
SELECT * FROM predictions WHERE is_event_match = TRUE LIMIT 10;

-- Breakdown par type d'événement
SELECT 
    event_context,
    event_name,
    event_phase,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'WON') as wins,
    COUNT(*) FILTER (WHERE status = 'LOST') as losses,
    ROUND(AVG(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) * 100, 1) as win_rate
FROM predictions 
WHERE is_event_match = TRUE
GROUP BY event_context, event_name, event_phase
ORDER BY total DESC;

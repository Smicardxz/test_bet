-- =====================================================
-- EVENT MODE MIGRATION SQL FINAL - SUPABASE (CORRIGÉ)
-- =====================================================
-- Exécuter cette requête complète dans Supabase SQL Editor
-- =====================================================

-- 1. Vérifier que la table predictions existe
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_name = 'predictions';

-- 2. Ajouter les colonnes EVENT_MODE une par une (syntaxe corrigée)
ALTER TABLE predictions 
ADD COLUMN IF NOT EXISTS event_context TEXT DEFAULT 'DOMESTIC_LEAGUE';

ALTER TABLE predictions 
ADD COLUMN IF NOT EXISTS event_name TEXT;

ALTER TABLE predictions 
ADD COLUMN IF NOT EXISTS is_event_match BOOLEAN DEFAULT FALSE;

ALTER TABLE predictions 
ADD COLUMN IF NOT EXISTS event_phase TEXT DEFAULT 'unknown_phase';

-- 3. Vérifier que les colonnes ont été ajoutées correctement
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'predictions' 
  AND column_name IN ('event_context', 'event_name', 'is_event_match', 'event_phase')
ORDER BY column_name;

-- 4. Créer les index pour optimiser les performances
CREATE INDEX IF NOT EXISTS idx_predictions_event_context 
ON predictions(event_context);

CREATE INDEX IF NOT EXISTS idx_predictions_is_event_match 
ON predictions(is_event_match);

CREATE INDEX IF NOT EXISTS idx_predictions_event_name 
ON predictions(event_name);

-- 5. Ajouter les commentaires aux colonnes
COMMENT ON COLUMN predictions.event_context IS 'Event context: DOMESTIC_LEAGUE, INTERNATIONAL_FRIENDLY, WORLD_CUP, CONTINENTAL_TOURNAMENT, YOUTH_TOURNAMENT, UNKNOWN_EVENT';

COMMENT ON COLUMN predictions.event_name IS 'Human-readable event name (e.g., FIFA World Cup 2026, International Friendlies)';

COMMENT ON COLUMN predictions.is_event_match IS 'True if match is an event (non-domestic league)';

COMMENT ON COLUMN predictions.event_phase IS 'Event phase: qualification, group_stage, knockout_round, semi_final, final, warmup, unknown_phase';

-- 6. Mettre à jour les prédictions existantes avec les bonnes valeurs
-- (uniquement si vous avez déjà des prédictions dans la table)
UPDATE predictions 
SET 
    event_context = CASE 
        WHEN LOWER(league) LIKE '%world cup%' OR LOWER(league) LIKE '%fifa world cup%' THEN 'WORLD_CUP'
        WHEN LOWER(league) LIKE '%euro%' OR LOWER(league) LIKE '%european championship%' THEN 'CONTINENTAL_TOURNAMENT'
        WHEN LOWER(league) LIKE '%copa america%' OR LOWER(league) LIKE '%afcon%' OR LOWER(league) LIKE '%asian cup%' OR LOWER(league) LIKE '%gold cup%' OR LOWER(league) LIKE '%nations league%' THEN 'CONTINENTAL_TOURNAMENT'
        WHEN LOWER(league) LIKE '%u20%' OR LOWER(league) LIKE '%u21%' OR LOWER(league) LIKE '%u19%' OR LOWER(league) LIKE '%u17%' OR LOWER(league) LIKE '%under-20%' OR LOWER(league) LIKE '%under-21%' OR LOWER(league) LIKE '%under-19%' OR LOWER(league) LIKE '%under-17%' OR LOWER(league) LIKE '%youth%' OR LOWER(league) LIKE '%junior%' THEN 'YOUTH_TOURNAMENT'
        WHEN LOWER(league) LIKE '%friendly%' OR LOWER(league) LIKE '%friendlies%' OR LOWER(league) LIKE '%international friendly%' THEN 'INTERNATIONAL_FRIENDLY'
        ELSE 'DOMESTIC_LEAGUE'
    END,
    is_event_match = CASE 
        WHEN LOWER(league) LIKE '%world cup%' OR LOWER(league) LIKE '%fifa world cup%' THEN TRUE
        WHEN LOWER(league) LIKE '%euro%' OR LOWER(league) LIKE '%european championship%' THEN TRUE
        WHEN LOWER(league) LIKE '%copa america%' OR LOWER(league) LIKE '%afcon%' OR LOWER(league) LIKE '%asian cup%' OR LOWER(league) LIKE '%gold cup%' OR LOWER(league) LIKE '%nations league%' THEN TRUE
        WHEN LOWER(league) LIKE '%u20%' OR LOWER(league) LIKE '%youth%' THEN TRUE
        WHEN LOWER(league) LIKE '%friendly%' OR LOWER(league) LIKE '%friendlies%' OR LOWER(league) LIKE '%international friendly%' THEN TRUE
        ELSE FALSE
    END,
    event_name = CASE 
        WHEN LOWER(league) LIKE '%world cup%' OR LOWER(league) LIKE '%fifa world cup%' THEN 'FIFA World Cup 2026'
        WHEN LOWER(league) LIKE '%euro%' OR LOWER(league) LIKE '%european championship%' THEN 'UEFA European Championship'
        WHEN LOWER(league) LIKE '%copa america%' THEN 'Copa América'
        WHEN LOWER(league) LIKE '%afcon%' OR LOWER(league) LIKE '%africa cup%' THEN 'Africa Cup of Nations'
        WHEN LOWER(league) LIKE '%asian cup%' THEN 'AFC Asian Cup'
        WHEN LOWER(league) LIKE '%gold cup%' THEN 'CONCACAF Gold Cup'
        WHEN LOWER(league) LIKE '%nations league%' THEN 'UEFA Nations League'
        WHEN LOWER(league) LIKE '%friendly%' OR LOWER(league) LIKE '%friendlies%' OR LOWER(league) LIKE '%international friendly%' THEN 'International Friendlies'
        WHEN LOWER(league) LIKE '%u20%' OR LOWER(league) LIKE '%youth%' THEN league
        ELSE league
    END,
    event_phase = CASE 
        WHEN LOWER(league) LIKE '%qualification%' OR LOWER(league) LIKE '%qualifier%' OR LOWER(league) LIKE '%qualifying%' THEN 'qualification'
        WHEN LOWER(league) LIKE '%group%' THEN 'group_stage'
        WHEN LOWER(league) LIKE '%final%' THEN 'final'
        WHEN LOWER(league) LIKE '%semi%' THEN 'semi_final'
        WHEN LOWER(league) LIKE '%knockout%' OR LOWER(league) LIKE '%round of%' THEN 'knockout_round'
        WHEN LOWER(league) LIKE '%friendly%' OR LOWER(league) LIKE '%friendlies%' OR LOWER(league) LIKE '%international friendly%' THEN 'warmup'
        ELSE 'unknown_phase'
    END
WHERE event_context IS NULL OR event_context = 'DOMESTIC_LEAGUE';

-- 7. Vérifier les résultats de la mise à jour
SELECT 
    event_context,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE is_event_match = TRUE) as event_matches,
    COUNT(*) FILTER (WHERE is_event_match = FALSE) as domestic_matches,
    ROUND(COUNT(*) FILTER (WHERE is_event_match = TRUE) * 100.0 / COUNT(*), 1) as event_percentage
FROM predictions 
GROUP BY event_context 
ORDER BY total_count DESC;

-- 8. Exemples de requêtes pour vérifier les données
-- Tous les matchs World Cup
SELECT 
    home_team, 
    away_team, 
    league, 
    event_context, 
    event_name, 
    event_phase, 
    is_event_match,
    created_at
FROM predictions 
WHERE event_context = 'WORLD_CUP' 
ORDER BY created_at DESC 
LIMIT 10;

-- Tous les matchs événements
SELECT 
    event_context,
    event_name,
    event_phase,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'WON') as wins,
    COUNT(*) FILTER (WHERE status = 'LOST') as losses,
    COUNT(*) FILTER (WHERE status = 'PENDING') as pending,
    ROUND(AVG(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) * 100, 1) as win_rate
FROM predictions 
WHERE is_event_match = TRUE
GROUP BY event_context, event_name, event_phase
ORDER BY total DESC;

-- 9. Statistiques globales des événements
SELECT 
    COUNT(*) as total_predictions,
    COUNT(*) FILTER (WHERE is_event_match = TRUE) as total_event_predictions,
    COUNT(*) FILTER (WHERE is_event_match = FALSE) as total_domestic_predictions,
    ROUND(COUNT(*) FILTER (WHERE is_event_match = TRUE) * 100.0 / COUNT(*), 1) as event_percentage,
    COUNT(DISTINCT event_context) as distinct_event_types,
    COUNT(DISTINCT event_name) as distinct_event_names
FROM predictions;

-- 10. Vérification finale - toutes les colonnes EVENT_MODE
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'predictions' 
  AND column_name IN ('event_context', 'event_name', 'is_event_match', 'event_phase')
ORDER BY column_name;

-- 11. Vérifier la structure de la table predictions (pour débogage)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'predictions'
ORDER BY column_name
LIMIT 20;

-- =====================================================
-- FIN DE LA MIGRATION EVENT_MODE (CORRIGÉ)
-- =====================================================

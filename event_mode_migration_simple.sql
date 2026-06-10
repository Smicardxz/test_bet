-- EVENT MODE MIGRATION SQL SIMPLIFIÉE
-- Exécuter cette requête dans Supabase SQL Editor

-- 1. Vérifier d'abord si la table predictions existe
SELECT table_name FROM information_schema.tables WHERE table_name = 'predictions';

-- 2. Ajouter les colonnes une par une (plus sûr)
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS event_context TEXT DEFAULT 'DOMESTIC_LEAGUE';

ALTER TABLE predictions ADD COLUMN IF NOT EXISTS event_name TEXT;

ALTER TABLE predictions ADD COLUMN IF NOT EXISTS is_event_match BOOLEAN DEFAULT FALSE;

ALTER TABLE predictions ADD COLUMN IF NOT EXISTS event_phase TEXT DEFAULT 'unknown_phase';

-- 3. Vérifier que les colonnes ont été ajoutées
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'predictions' 
  AND column_name IN ('event_context', 'event_name', 'is_event_match', 'event_phase')
ORDER BY column_name;

-- 4. Créer les index
CREATE INDEX IF NOT EXISTS idx_predictions_event_context ON predictions(event_context);
CREATE INDEX IF NOT EXISTS idx_predictions_is_event_match ON predictions(is_event_match);

-- 5. Mettre à jour les prédictions existantes (si vous avez des données)
UPDATE predictions 
SET event_context = CASE 
    WHEN LOWER(competition_name) LIKE '%world cup%' OR LOWER(competition_name) LIKE '%fifa world cup%' THEN 'WORLD_CUP'
    WHEN LOWER(competition_name) LIKE '%euro%' OR LOWER(competition_name) LIKE '%european championship%' THEN 'CONTINENTAL_TOURNAMENT'
    WHEN LOWER(competition_name) LIKE '%friendly%' OR LOWER(competition_name) LIKE '%friendlies%' OR LOWER(competition_name) LIKE '%international friendly%' THEN 'INTERNATIONAL_FRIENDLY'
    WHEN LOWER(competition_name) LIKE '%u20%' OR LOWER(competition_name) LIKE '%u21%' OR LOWER(competition_name) LIKE '%u19%' OR LOWER(competition_name) LIKE '%u17%' OR LOWER(competition_name) LIKE '%under-20%' OR LOWER(competition_name) LIKE '%under-21%' OR LOWER(competition_name) LIKE '%under-19%' OR LOWER(competition_name) LIKE '%under-17%' OR LOWER(competition_name) LIKE '%youth%' OR LOWER(competition_name) LIKE '%junior%' THEN 'YOUTH_TOURNAMENT'
    ELSE 'DOMESTIC_LEAGUE'
END,
is_event_match = CASE 
    WHEN LOWER(competition_name) LIKE '%world cup%' OR LOWER(competition_name) LIKE '%fifa world cup%' THEN TRUE
    WHEN LOWER(competition_name) LIKE '%euro%' OR LOWER(competition_name) LIKE '%european championship%' THEN TRUE
    WHEN LOWER(competition_name) LIKE '%friendly%' OR LOWER(competition_name) LIKE '%friendlies%' OR LOWER(competition_name) LIKE '%international friendly%' THEN TRUE
    WHEN LOWER(competition_name) LIKE '%u20%' OR LOWER(competition_name) LIKE '%youth%' THEN TRUE
    ELSE FALSE
END,
event_name = CASE 
    WHEN LOWER(competition_name) LIKE '%world cup%' OR LOWER(competition_name) LIKE '%fifa world cup%' THEN 'FIFA World Cup 2026'
    WHEN LOWER(competition_name) LIKE '%euro%' OR LOWER(competition_name) LIKE '%european championship%' THEN 'UEFA European Championship'
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

-- Question 1: How much usable observation history does each object have?
SELECT
    o.oid,
    COUNT(DISTINCT d.candid) AS detection_count
FROM objects o
LEFT JOIN detections AS d ON o.oid = d.oid
GROUP BY o.oid
ORDER BY detection_count, o.oid;

-- Question 3. Which objects are missing classifications?
SELECT 
	o.oid
FROM objects AS o
LEFT JOIN probabilities AS p
	ON o.oid = p.oid
WHERE p.oid IS NULL;

-- 5. What classes each classifier prefer?
WITH coverage AS (
    SELECT
        p.classifier_name,
        p.classifier_version,
        COUNT(DISTINCT p.oid) AS coverage_count
    FROM probabilities AS p
    GROUP BY
        p.classifier_name,
        p.classifier_version
),

class_counts AS (
    SELECT
        p.classifier_name,
        p.classifier_version,
        p.class_name,
        COUNT(DISTINCT p.oid) AS class_count
    FROM probabilities AS p
    WHERE p.ranking = 1
    GROUP BY
        p.classifier_name,
        p.classifier_version,
        p.class_name
),

ranked_classes AS (
    SELECT
        cc.*,
        ROW_NUMBER() OVER (
            PARTITION BY cc.classifier_name, cc.classifier_version
            ORDER BY cc.class_count DESC, cc.class_name
        ) AS class_rank
    FROM class_counts AS cc
)

SELECT
    c.classifier_name,
    c.classifier_version,
    c.coverage_count,

    MAX(CASE
        WHEN rc.class_rank = 1 THEN rc.class_name
    END) AS top_class_1,

	MAX(CASE
	    WHEN rc.class_rank = 1
	    THEN ROUND(100.0 * rc.class_count / c.coverage_count, 2)
	END) AS top_class_1_share,

    MAX(CASE
        WHEN rc.class_rank = 2 THEN rc.class_name
    END) AS top_class_2,

    MAX(CASE
        WHEN rc.class_rank = 2
        THEN ROUND(100.0 * rc.class_count / c.coverage_count, 2)
    END) AS top_class_2_share

FROM coverage AS c
LEFT JOIN ranked_classes AS rc
    ON c.classifier_name = rc.classifier_name
    AND c.classifier_version = rc.classifier_version

GROUP BY
    c.classifier_name,
    c.classifier_version,
    c.coverage_count

ORDER BY
    c.classifier_name,
    c.classifier_version,
    c.coverage_count DESC;


-- 5. What classes and confidence levels would the chosen pair contribute?
-- lc_classifier_BHRF_forced_phot
-- 2.1.0
SELECT 
    p.class_name,
    COUNT(*) AS class_counts,
    ROUND(
        PERCENTILE_CONT(0.5) 
        WITHIN GROUP (ORDER BY p.probability)::numeric, 2
    ) AS median_probability
FROM probabilities AS p
WHERE p.classifier_name = 'lc_classifier_BHRF_forced_phot'
  AND p.classifier_version = '2.1.0'
  AND p.ranking = 1
GROUP BY p.class_name;


-- 6. What dates and observation histories does this sample cover?
SELECT 
	MIN(observed_at) AS earlist_time,
	MAX(observed_at) AS latest_time
FROM detections;


-- 6. For the selected classifier, how many times a NOVA/CV has beed observed? Its observation duration?
SELECT  
    DISTINCT p.oid,
    ndet,
	p.class_name,
	ROUND(p.probability::numeric, 2) AS probability,
    o.first_observed_at,
    o.last_observed_at,
    (o.last_observed_at::date - o.first_observed_at::date) AS observation_days
FROM probabilities AS p
LEFT JOIN objects AS o
    USING (oid)
WHERE p.classifier_name = 'lc_classifier_BHRF_forced_phot'
  AND p.classifier_version = '2.1.0'
  AND p.ranking = 1
  AND class_name = 'CV/Nova';

-- Teableau set up
-- 518 candidates cv/nova from choosen classifier
CREATE TEMP VIEW cv_candidates AS
SELECT DISTINCT
    p.oid,
    o.ndet,
    p.class_name,
    p.probability,
    o.first_observed_at,
    o.last_observed_at,
    (o.last_observed_at::date - o.first_observed_at::date) AS observation_days
FROM probabilities AS p
LEFT JOIN objects AS o
    ON p.oid = o.oid
WHERE p.classifier_name = 'lc_classifier_BHRF_forced_phot'
  AND p.classifier_version = '2.1.0'
  AND p.ranking = 1
  AND p.class_name = 'CV/Nova';


-- cv_detections: JOIN cv_candidates with their detection history
CREATE TEMP VIEW cv_detections AS
SELECT DISTINCT d.*
FROM cv_candidates AS cv_c
JOIN detections AS d
    ON cv_c.oid = d.oid;


-- cv_observation_support: 518 rows, light spectrum counts, observation spam/day_count/since observed
SET TIME ZONE 'UTC';
CREATE TEMP VIEW cv_observation_support AS
SELECT
    cv_d.oid,

    COUNT(*) AS detection_count,
    COUNT(DISTINCT cv_d.observed_at::date) AS observing_day_count,

    COUNT(*) FILTER (WHERE cv_d.fid = 1) AS g_count,
    COUNT(*) FILTER (WHERE cv_d.fid = 2) AS r_count,
    COUNT(*) FILTER (WHERE cv_d.fid = 3) AS i_count,

    COUNT(*) FILTER (WHERE cv_d.isdiffpos = 1) AS positive_count,
    COUNT(*) FILTER (WHERE cv_d.isdiffpos = -1) AS negative_count,

    MIN(cv_d.observed_at) AS first_observed_at,
    MAX(cv_d.observed_at) AS last_observed_at,

    (MAX(cv_d.observed_at)::date - MIN(cv_d.observed_at)::date) AS observation_spam,
	(DATE '2026-10-19' - MAX(cv_d.observed_at)::date) AS days_since_last_observation
	
FROM cv_detections AS cv_d
GROUP BY cv_d.oid;

-- cv_last_observe: observed since
CREATE TEMP VIEW cv_last_observation AS
SELECT 
	oid,
	(DATE '2026-10-19' - MAX(observed_at)::date) AS days_since_last_observation
FROM cv_detections AS cv_d
GROUP BY oid
ORDER BY days_since_last_observation;

-- Luminosity_1_var: 90th - 10th mag, recent mag, fid=1, isdiffpos=1
CREATE TEMP VIEW cv_mag_1_var AS
WITH tmp as (
	SELECT 
		oid,
		PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY magpsf) - 
		PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY magpsf) AS amplitude_diff,
		MAX(observed_at) AS observed_at
	FROM cv_detections
	WHERE isdiffpos = 1 AND fid=1
	GROUP BY oid
	HAVING COUNT(*) >= 3
)

SELECT 
	oid, 
	amplitude_diff, 
	magpsf, 
	sigmapsf, 
	tmp.observed_at
FROM tmp
LEFT JOIN cv_detections
	USING (oid, observed_at);


-- Luminosity_1_var: 90th - 10th mag, recent mag, fid=2, isdiffpos=1
CREATE TEMP VIEW cv_mag_2_var AS
with tmp as (
	SELECT 
		oid,
		PERCENTILE_CONT(0.9) WITHIN GROUP(ORDER BY magpsf) -
		PERCENTILE_CONT(0.1) WITHIN GROUP(ORDER BY magpsf) AS amplitude_diff,
		MAX(observed_at) AS observed_at
	FROM cv_detections
	WHERE fid=2 AND isdiffpos=1
	GROUP BY oid
	HAVING COUNT(*) >= 3
)

SELECT 
	oid,
	amplitude_diff,
	magpsf,
	sigmapsf,
	observed_at
FROM tmp
LEFT JOIN cv_detections
	USING (oid, observed_at)
WHERE fid=2 AND isdiffpos=1;

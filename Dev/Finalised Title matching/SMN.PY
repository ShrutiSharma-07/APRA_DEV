#ENHANCED MATCHING SCRIPT WITH COMPLETE CARTESIAN PRODUCT - UNIFIED IMPLEMENTATION

def create_enhanced_udf(session):
    """Create enhanced JavaScript UDF for name matching with multiple format handling"""
    
    create_udf_sql = """
    CREATE OR REPLACE FUNCTION ENHANCED_MATCH_COMPOSER_NAMES(name1 STRING, name2 STRING)
    RETURNS OBJECT
    LANGUAGE JAVASCRIPT
    AS
    $$
    
    /**
     * Normalize names to handle special cases:
     * 1. Remove/normalize generational suffixes
     * 2. Replace hyphens with spaces to handle hyphenated names
     * 3. Normalize special prefixes
     * 4. Remove bracket content
     */
    function normalizeNameForComparison(name) {
        if (!name) return "";
        
        // Remove content in brackets first
        name = name.replace(/\\([^\\)]*\\)/g, "");
        
        name = name.toUpperCase().trim();
        
        // 1. Remove generational suffixes: I, II, III, IV, V and their variations
        name = name.replace(/\\b(I{1,3}|IV|V|1ST|2ND|3RD|[4-9]TH)\\b$/g, "").trim();
        
        // 2. Replace hyphens with spaces for better matching
        name = name.replace(/-/g, " ");
        
        // 3. Special handling for prefixes - ensure consistent spacing
        const special_prefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL", "DOS", "DA", "DU", "AL", "EL", "JESUS", "CHAVEZ"];
        
        // Create regex patterns for each prefix to match only when it's a standalone word
        for (const prefix of special_prefixes) {
            const regex = new RegExp(`\\\\b${prefix}\\\\b`, 'g');
            // Ensure consistent spacing for each prefix
            name = name.replace(regex, prefix);
        }
        
        // Remove extra whitespace
        name = name.replace(/\\s+/g, " ").trim();
        
        return name;
    }

    /**
     * Enhanced name parsing that handles multiple formats
     */
    function parseNameComponents(name) {
        if (!name || name === "") {
            return {formats: []};
        }

        // Normalize the name first
        name = normalizeNameForComparison(name);

        // Special suffixes and prefixes
        const suffixes = ["SENIOR", "SNR", "SR", "JUNIOR", "JNR", "JR"];
        const special_prefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL", "DOS", "DA", "DU", "AL", "EL", "JESUS", "CHAVEZ"];

        // Clean and split the name
        let parts = name.split(/\\s+/);

        // Handle name with no spaces
        if (parts.length === 1) {
            return {formats: [{first: "", last: parts[0], middle: "", suffix: "", is_initial: false}]};
        }

        // Check for and extract suffixes
        let suffix = "";
        for (const suffixTerm of suffixes) {
            const suffixIndex = parts.findIndex(part => part === suffixTerm);
            if (suffixIndex !== -1) {
                suffix = parts[suffixIndex];
                parts.splice(suffixIndex, 1);
                break;
            }
        }

        // After removing suffix, check if we're back to a single name
        if (parts.length === 1) {
            return {formats: [{first: "", last: parts[0], middle: "", suffix: suffix, is_initial: false}]};
        }

        // Generate multiple format possibilities
        const formatsToCheck = [];
        
        // Check for special multi-word last names with prefixes like "VAN BEETHOVEN"
        let hasSpecialPrefix = false;
        let specialPrefixIndex = -1;
        
        for (let i = 0; i < parts.length; i++) {
            if (special_prefixes.includes(parts[i])) {
                hasSpecialPrefix = true;
                specialPrefixIndex = i;
                break;
            }
        }
        
        if (hasSpecialPrefix) {
            if (specialPrefixIndex === 0 && parts.length >= 2) {
                // Case: "VAN BEETHOVEN" or "VAN BEETHOVEN LUDWIG"
                if (parts.length === 2) {
                    // Just "VAN BEETHOVEN" - treat as compound last name
                    formatsToCheck.push({
                        first: "",
                        last: parts.join(" "),
                        middle: "",
                        suffix: suffix,
                        is_initial: false
                    });
                } else {
                    // "BEETHOVEN LUDWIG VAN" - LASTNAME FIRSTNAME PREFIX format
                    formatsToCheck.push({
                        first: parts[1],
                        last: parts[0] + " " + parts[2],
                        middle: parts.slice(3).join(" "),
                        suffix: suffix,
                        is_initial: parts[1] && parts[1].length === 1
                    });
                    
                    // "VAN BEETHOVEN LUDWIG" - PREFIX LASTNAME FIRSTNAME format
                    const lastName = parts.slice(0, 2).join(" ");
                    const firstName = parts[2];
                    const middleName = parts.slice(3).join(" ");
                    
                    formatsToCheck.push({
                        first: firstName,
                        last: lastName,
                        middle: middleName,
                        suffix: suffix,
                        is_initial: firstName && firstName.length === 1
                    });
                }
            } else if (specialPrefixIndex > 0) {
                // Case: "LUDWIG VAN BEETHOVEN" - FIRSTNAME PREFIX LASTNAME format
                const firstName = parts.slice(0, specialPrefixIndex).join(" ");
                const lastName = parts.slice(specialPrefixIndex).join(" ");
                
                formatsToCheck.push({
                    first: firstName,
                    last: lastName,
                    middle: "",
                    suffix: suffix,
                    is_initial: firstName.length === 1
                });
                
                // Also try reversed: LASTNAME FIRSTNAME format (VAN BEETHOVEN LUDWIG)
                formatsToCheck.push({
                    first: firstName,
                    last: lastName,
                    middle: "",
                    suffix: suffix,
                    is_initial: firstName.length === 1
                });
            }
        }
        
        // Standard format handling for all cases
        if (parts.length === 2) {
            // Two parts: ALWAYS try both orders for cases like "BERNIE BEN" vs "BEN BERNIE"
            formatsToCheck.push({
                first: parts[0],
                last: parts[1],
                middle: "",
                suffix: suffix,
                is_initial: parts[0].length === 1
            });
            
            formatsToCheck.push({
                first: parts[1],
                last: parts[0],
                middle: "",
                suffix: suffix,
                is_initial: parts[1].length === 1
            });
        } else if (parts.length >= 3) {
            // Format 1: LASTNAME FIRSTNAME MIDDLENAME (ADC Style)
            formatsToCheck.push({
                first: parts[1],
                last: parts[0],
                middle: parts.slice(2).join(" "),
                suffix: suffix,
                is_initial: parts[1].length === 1
            });
            
            // Format 2: FIRSTNAME MIDDLENAME LASTNAME (Muzooka Style)
            formatsToCheck.push({
                first: parts[0],
                last: parts[parts.length - 1],
                middle: parts.slice(1, parts.length - 1).join(" "),
                suffix: suffix,
                is_initial: parts[0].length === 1
            });
            
            // Format 3: FIRSTNAME LASTNAME (treating middle as part of first)
            formatsToCheck.push({
                first: parts.slice(0, parts.length - 1).join(" "),
                last: parts[parts.length - 1],
                middle: "",
                suffix: suffix,
                is_initial: false
            });
            
            // Format 4: LASTNAME FIRSTNAME (treating middle as part of last)
            formatsToCheck.push({
                first: parts[parts.length - 1],
                last: parts.slice(0, parts.length - 1).join(" "),
                middle: "",
                suffix: suffix,
                is_initial: parts[parts.length - 1].length === 1
            });
            
            // Format 5: For compound last names (first two parts as last name)
            if (parts.length >= 3) {
                formatsToCheck.push({
                    first: parts.slice(2).join(" "),
                    last: parts.slice(0, 2).join(" "),
                    middle: "",
                    suffix: suffix,
                    is_initial: false
                });
            }
            
            // Format 6: For compound last names (last two parts as last name)
            if (parts.length >= 3) {
                formatsToCheck.push({
                    first: parts.slice(0, parts.length - 2).join(" "),
                    last: parts.slice(parts.length - 2).join(" "),
                    middle: "",
                    suffix: suffix,
                    is_initial: false
                });
            }
        }

        return {formats: formatsToCheck};
    }

    /**
     * Calculate string similarity using Levenshtein distance
     */
    function calculateStringSimilarity(s1, s2) {
        if (!s1 || !s2) return 0;
        if (s1 === s2) return 1.0;

        const str1 = s1.toUpperCase().trim();
        const str2 = s2.toUpperCase().trim();

        if (str1 === str2) return 1.0;
        if (str1 === "" || str2 === "") return 0.0;

        const len1 = str1.length;
        const len2 = str2.length;
        const matrix = Array(len1 + 1).fill().map(() => Array(len2 + 1).fill(0));

        for (let i = 0; i <= len1; i++) matrix[i][0] = i;
        for (let j = 0; j <= len2; j++) matrix[0][j] = j;

        for (let i = 1; i <= len1; i++) {
            for (let j = 1; j <= len2; j++) {
                const cost = str1[i-1] === str2[j-1] ? 0 : 1;
                matrix[i][j] = Math.min(
                    matrix[i-1][j] + 1,
                    matrix[i][j-1] + 1,
                    matrix[i-1][j-1] + cost
                );
            }
        }

        const distance = matrix[len1][len2];
        const maxLen = Math.max(len1, len2);
        return 1 - (distance / maxLen);
    }

    /**
     * Jaro-Winkler similarity implementation
     */
    function jaroWinklerSimilarity(s1, s2) {
        if (!s1 || !s2 || s1.length === 0 || s2.length === 0) return 0;
        if (s1 === s2) return 1;
        
        let m = 0;
        let t = 0;
        let range = Math.floor(Math.max(s1.length, s2.length) / 2) - 1;
        range = Math.max(0, range);
        
        let s1Matches = new Array(s1.length).fill(false);
        let s2Matches = new Array(s2.length).fill(false);
        
        for (let i = 0; i < s1.length; i++) {
            let start = Math.max(0, i - range);
            let end = Math.min(i + range + 1, s2.length);
            
            for (let j = start; j < end; j++) {
                if (!s2Matches[j] && s1[i] === s2[j]) {
                    s1Matches[i] = true;
                    s2Matches[j] = true;
                    m++;
                    break;
                }
            }
        }
        
        if (m === 0) return 0;
        
        let k = 0;
        for (let i = 0; i < s1.length; i++) {
            if (s1Matches[i]) {
                while (k < s2.length && !s2Matches[k]) k++;
                if (k < s2.length && s1[i] !== s2[k]) t++;
                if (k < s2.length) k++;
            }
        }
        
        t = Math.floor(t / 2);
        let jaroSim = (m / s1.length + m / s2.length + (m - t) / m) / 3;
        
        let p = 0.1;
        let l = 0;
        
        for (let i = 0; i < Math.min(4, Math.min(s1.length, s2.length)); i++) {
            if (s1[i] === s2[i]) {
                l++;
            } else {
                break;
            }
        }
        
        return jaroSim + (l * p * (1 - jaroSim));
    }

    /**
     * Calculate match score between two name formats with enhanced logic
     */
    function calculateMatchScore(format1, format2) {
        if (!format1 || !format2) return 0;

        const first1 = format1.first || "";
        const last1 = format1.last || "";
        const middle1 = format1.middle || "";
        
        const first2 = format2.first || "";
        const last2 = format2.last || "";
        const middle2 = format2.middle || "";

        // Last name similarity (most important)
        const lastNameScore = calculateStringSimilarity(last1, last2);
        
        // First name similarity with enhanced initial handling
        let firstNameScore = 0;
        if (first1 && first2) {
            // Handle initials vs full names
            if ((first1.length === 1 && first2.length > 1) || (first2.length === 1 && first1.length > 1)) {
                const initial1 = first1.charAt(0);
                const initial2 = first2.charAt(0);
                firstNameScore = initial1 === initial2 ? 0.9 : 0; // Increased from 0.8 to 0.9
            } else {
                firstNameScore = calculateStringSimilarity(first1, first2);
            }
        } else if (!first1 && !first2) {
            firstNameScore = 1.0; // Both empty, perfect match
        }
        
        // Middle name similarity (more lenient)
        let middleNameScore = 1.0; // Changed from 0.7 to 1.0 when both empty
        if (middle1 && middle2) {
            middleNameScore = calculateStringSimilarity(middle1, middle2);
        } else if ((middle1 && !middle2) || (!middle1 && middle2)) {
            middleNameScore = 0.8; // Increased penalty for missing middle name
        }

        // Check for perfect match
        if (lastNameScore === 1.0 && firstNameScore === 1.0 && middleNameScore === 1.0) {
            return 1.0;
        }

        // Enhanced weighted score calculation
        let totalScore = 0;
        
        // Last name is most important (65% weight)
        totalScore += lastNameScore * 0.65;
        
        // First name is important (30% weight)
        totalScore += firstNameScore * 0.30;
        
        // Middle name has small weight (5% weight)
        totalScore += middleNameScore * 0.05;

        return Math.min(1.0, totalScore);
    }

    /**
     * Main enhanced name matching function
     */
    function enhancedMatchComposerNames(name1, name2) {
        try {
            if (!name1 || !name2 || name1.length === 0 || name2.length === 0) {
                return {
                    jaro_winkler_score: 0.0,
                    enhanced_score: 0.0,
                    best_format_match: 0.0,
                    normalized_match: 0.0
                };
            }
            
            // Clean and normalize inputs
            let cleanName1 = name1.toString().trim().toUpperCase();
            let cleanName2 = name2.toString().trim().toUpperCase();
            
            // Calculate original Jaro-Winkler for backward compatibility
            const jaroWinklerScore = jaroWinklerSimilarity(cleanName1, cleanName2);
            
            // Check for direct match after normalization
            const normalizedName1 = normalizeNameForComparison(name1);
            const normalizedName2 = normalizeNameForComparison(name2);
            
            let normalizedMatch = 0.0;
            if (normalizedName1 === normalizedName2) {
                normalizedMatch = 1.0;
            } else {
                normalizedMatch = calculateStringSimilarity(normalizedName1, normalizedName2);
            }
            
            // OPTION 1: ADD EXACT REVERSAL CHECK
            // Check for exact reversal match (for 2-part and 3-part names)
            const parts1 = normalizedName1.split(/\\s+/);
            const parts2 = normalizedName2.split(/\\s+/);
            
            // Handle 2-part names: "GORE MICHAEL" vs "MICHAEL GORE"
            if (parts1.length === 2 && parts2.length === 2) {
                if (parts1[0] === parts2[1] && parts1[1] === parts2[0]) {
                    return {
                        jaro_winkler_score: jaroWinklerScore,
                        enhanced_score: 1.0,
                        best_format_match: 1.0,
                        normalized_match: 1.0
                    };
                }
            }
            
            // Handle 3-part names: "URIETA MARTIN SOLANO" vs "MARTIN URIETA SOLANO"
            if (parts1.length === 3 && parts2.length === 3) {
                // Check if it's a simple reordering of the same three names
                const sorted1 = parts1.slice().sort();
                const sorted2 = parts2.slice().sort();
                
                if (sorted1.length === sorted2.length && 
                    sorted1.every((val, index) => val === sorted2[index])) {
                    return {
                        jaro_winkler_score: jaroWinklerScore,
                        enhanced_score: 1.0,
                        best_format_match: 1.0,
                        normalized_match: 1.0
                    };
                }
            }
            
            // Handle general case: check if both names contain exactly the same words
            if (parts1.length === parts2.length && parts1.length > 1) {
                const sorted1 = parts1.slice().sort();
                const sorted2 = parts2.slice().sort();
                
                if (sorted1.length === sorted2.length && 
                    sorted1.every((val, index) => val === sorted2[index])) {
                    return {
                        jaro_winkler_score: jaroWinklerScore,
                        enhanced_score: 1.0,
                        best_format_match: 1.0,
                        normalized_match: 1.0
                    };
                }
            }
            
            // Parse names into different formats
            const parsed1 = parseNameComponents(name1);
            const parsed2 = parseNameComponents(name2);
            
            // Try all format combinations and find the best match
            let bestFormatScore = 0;
            
            if (parsed1.formats && parsed2.formats) {
                for (const format1 of parsed1.formats) {
                    for (const format2 of parsed2.formats) {
                        const currentScore = calculateMatchScore(format1, format2);
                        bestFormatScore = Math.max(bestFormatScore, currentScore);
                    }
                }
            }
            
            // Calculate enhanced score combining multiple approaches
            const enhancedScore = Math.max(
                jaroWinklerScore,
                normalizedMatch,
                bestFormatScore
            );
            
            return {
                jaro_winkler_score: jaroWinklerScore,
                enhanced_score: enhancedScore,
                best_format_match: bestFormatScore,
                normalized_match: normalizedMatch
            };
            
        } catch (e) {
            return {
                jaro_winkler_score: 0.0,
                enhanced_score: 0.0,
                best_format_match: 0.0,
                normalized_match: 0.0
            };
        }
    }

    return enhancedMatchComposerNames(NAME1, NAME2);
    $$;
    """

    session.sql(create_udf_sql).collect()
    print("Enhanced JavaScript UDF for composer name matching created successfully.")


def create_unified_match_table(session, work_ids=None):
    """
    Create composer match table using the SAME implementation for both full and specific modes
    """
    
    # Build WHERE clause for work filtering - FIXED LOGIC
    mode_description = "ALL WORKS"
    
    if work_ids:
        work_ids_str = "', '".join(work_ids)
        work_ids_formatted = f"'{work_ids_str}'"
        where_clause_step1 = f"WHERE APRA_WORK_ID IN ({work_ids_formatted})"
        where_clause_step2 = f"WHERE APRA_WORK_ID IN ({work_ids_formatted}) AND MUZOOKA_TRACK_ID IS NOT NULL"
        mode_description = f"SPECIFIC WORKS: {work_ids}"
    else:
        where_clause_step1 = ""  # No filtering for full mode
        where_clause_step2 = "WHERE MUZOOKA_TRACK_ID IS NOT NULL"  # Only filter out NULL tracks
    
    print(f"Creating unified match table for {mode_description}...")
    print("Goal: Exactly one row per unique COMPOSER_NAME × MUZOOKA_TRACK_ID combination")
    
    # Single comprehensive query that creates the complete result set
    unified_sql = f"""
    WITH 
    -- Step 1: Get DISTINCT composer names per work (deduplicate by COMPOSER_NAME)
    unique_composer_names AS (
        SELECT DISTINCT
            APRA_WORK_ID,
            COMPOSER_NAME AS APRA_COMPOSER_NAME,
            -- Get any associated metadata for this composer name
            MIN(ADC_COMPOSER_ID) AS ADC_COMPOSER_ID,  -- Use MIN to get one ID per name
            MIN(RDC_WORKS_ID) AS RDC_WORKS_ID,
            MIN(IPI) AS ADC_IPI,
            MIN(APRA_COMPOSER_CT) AS APRA_COMPOSER_CT,
            MIN(APRA_TOTAL_COMPOSERS) AS APRA_TOTAL_COMPOSERS
        FROM ADC_COMPOSER_DELIMITER_COUNT_CLEAN
        {where_clause_step1}
        GROUP BY APRA_WORK_ID, COMPOSER_NAME
    ),
    
    -- Step 2: Get unique tracks per work - FIXED WHERE CLAUSE
    unique_tracks AS (
        SELECT DISTINCT
            APRA_WORK_ID,
            MUZOOKA_TRACK_ID
        FROM ADC_COMPOSER_DELIMITER_COUNT_CLEAN
        {where_clause_step2}
    ),
    
    -- Step 3: Get Muzooka track metadata
    track_metadata AS (
        SELECT DISTINCT
            MUZOOKA_TRACK_ID,
            MZK_TOTAL_COMPOSERS,
            IPI
        FROM MZK_COMPOSER_DELIMITER_COUNT_CLEAN
    ),
    
    -- Step 4: Create COMPLETE CARTESIAN PRODUCT (every unique composer name x every track per work)
    complete_combinations AS (
        SELECT 
            c.APRA_WORK_ID,
            c.ADC_COMPOSER_ID,
            c.RDC_WORKS_ID,
            c.APRA_COMPOSER_NAME,
            c.ADC_IPI,
            c.APRA_COMPOSER_CT,
            c.APRA_TOTAL_COMPOSERS,
            t.MUZOOKA_TRACK_ID,
            COALESCE(tm.MZK_TOTAL_COMPOSERS, 0) AS MZK_TOTAL_COMPOSERS
        FROM unique_composer_names c
        CROSS JOIN unique_tracks t
        LEFT JOIN track_metadata tm ON t.MUZOOKA_TRACK_ID = tm.MUZOOKA_TRACK_ID
        WHERE c.APRA_WORK_ID = t.APRA_WORK_ID
    ),
    
    -- Step 5: Calculate name match scores for each combination
    composer_track_matches AS (
        SELECT 
            cc.APRA_WORK_ID,
            cc.ADC_COMPOSER_ID,
            cc.MUZOOKA_TRACK_ID,
            cc.APRA_COMPOSER_NAME,
            -- Calculate best match score for this composer against all Muzooka composers on this track
            COALESCE(MAX(ENHANCED_MATCH_COMPOSER_NAMES(cc.APRA_COMPOSER_NAME, m.COMPOSER_NAME):enhanced_score::FLOAT), 0.0) AS NAME_MATCH_SCORE
        FROM complete_combinations cc
        LEFT JOIN MZK_COMPOSER_DELIMITER_COUNT_CLEAN m
        ON cc.MUZOOKA_TRACK_ID = m.MUZOOKA_TRACK_ID
        GROUP BY cc.APRA_WORK_ID, cc.ADC_COMPOSER_ID, cc.MUZOOKA_TRACK_ID, cc.APRA_COMPOSER_NAME
    ),
    
    -- Step 6: Calculate writer match percentage at work-track level
    -- WRITER_MTCH_PCNTG = SUM(NAME_MATCH_SCORE) / MAX(APRA_TOTAL_COMPOSERS) 
    -- Grouped by APRA_WORK_ID + MUZOOKA_TRACK_ID combination
    work_track_writer_percentage AS (
        SELECT 
            ctm.APRA_WORK_ID,
            ctm.MUZOOKA_TRACK_ID,
            SUM(ctm.NAME_MATCH_SCORE) AS total_match_score,
            -- Get the actual APRA_TOTAL_COMPOSERS for this work
            MAX(cc.APRA_TOTAL_COMPOSERS) AS work_total_composers,
           
            CASE 
                WHEN MAX(cc.APRA_TOTAL_COMPOSERS) > 0 THEN
                    SUM(ctm.NAME_MATCH_SCORE) / MAX(cc.APRA_TOTAL_COMPOSERS)
                ELSE 0.0
            END AS WRITER_MTCH_PCNTG
        FROM composer_track_matches ctm
        JOIN complete_combinations cc 
            ON ctm.APRA_WORK_ID = cc.APRA_WORK_ID 
            AND ctm.MUZOOKA_TRACK_ID = cc.MUZOOKA_TRACK_ID
        GROUP BY ctm.APRA_WORK_ID, ctm.MUZOOKA_TRACK_ID  --  GROUPED BY WORK + TRACK
    )
    
    -- Step 7: Final result set
    SELECT
        cc.RDC_WORKS_ID,
        cc.ADC_COMPOSER_ID,
        cc.APRA_WORK_ID,
        cc.MUZOOKA_TRACK_ID,
        cc.ADC_IPI,
        CASE 
            WHEN cc.ADC_IPI IS NOT NULL AND tm.IPI IS NOT NULL AND cc.ADC_IPI = tm.IPI THEN 'Y' 
            ELSE 'N' 
        END AS YN_IPI_MATCH,
        cc.APRA_COMPOSER_NAME,
        cc.APRA_TOTAL_COMPOSERS,
        cc.MZK_TOTAL_COMPOSERS,
        COUNT(DISTINCT cc.APRA_COMPOSER_NAME) OVER (PARTITION BY cc.APRA_WORK_ID) AS APRA_MATCHED_TOTAL_COMPOSERS,
        0 AS PART_MATCH_SCORE,  -- Simplified for consistency
        cc.APRA_COMPOSER_CT,
        COALESCE(ctm.NAME_MATCH_SCORE, 0) AS NAME_MATCH_SCORE,
        ROUND(COALESCE(wtp.WRITER_MTCH_PCNTG, 0), 6) AS WRITER_MTCH_PCNTG
    FROM 
        complete_combinations cc
    LEFT JOIN 
        composer_track_matches ctm
    ON cc.APRA_WORK_ID = ctm.APRA_WORK_ID 
       AND cc.ADC_COMPOSER_ID = ctm.ADC_COMPOSER_ID 
       AND cc.MUZOOKA_TRACK_ID = ctm.MUZOOKA_TRACK_ID
    LEFT JOIN 
        work_track_writer_percentage wtp
    ON cc.APRA_WORK_ID = wtp.APRA_WORK_ID 
       AND cc.MUZOOKA_TRACK_ID = wtp.MUZOOKA_TRACK_ID
    LEFT JOIN 
        track_metadata tm
    ON cc.MUZOOKA_TRACK_ID = tm.MUZOOKA_TRACK_ID
    ORDER BY
        cc.APRA_WORK_ID, cc.APRA_COMPOSER_NAME, cc.MUZOOKA_TRACK_ID
    """
    
    # Execute and create the results table
    results = session.sql(unified_sql)
    
    # Choose table name based on mode
    table_name = "COMPOSER_NAME_MATCH_UNIFIED_FULL" if not work_ids else "COMPOSER_NAME_MATCH_UNIFIED_SPECIFIC"
    
    results.write.mode("overwrite").save_as_table(table_name)
    
    print(f" Table {table_name} created successfully!")
    print(f"Processing mode: {mode_description}")
    
    # Rest of the function remains the same...
    return table_name

def run_specific_works_pipeline(session, work_ids):
    """Run pipeline for specific work IDs using unified implementation"""
    
    if not work_ids:
        print("No work IDs provided.")
        return
    
    print(f"Running UNIFIED composer matching for work IDs: {work_ids}")
    
    # Create UDF first
    create_enhanced_udf(session)
    
    # Run unified pipeline for specific work IDs
    table_name = create_unified_match_table(session, work_ids)
    
    # Show detailed results for specific works if requested
    if 'GW39809338' in work_ids:
        print(f"\n=== DETAILED RESULTS FOR GW39809338 ===")
        detailed_sql = f"""
        SELECT 
            APRA_WORK_ID,
            MUZOOKA_TRACK_ID,
            APRA_COMPOSER_NAME,
            NAME_MATCH_SCORE,
            WRITER_MTCH_PCNTG
        FROM {table_name}
        WHERE APRA_WORK_ID = 'GW39809338'
        ORDER BY MUZOOKA_TRACK_ID, APRA_COMPOSER_NAME
        """
        
        detailed_results = session.sql(detailed_sql)
        detailed_results.show()
        
        # Show composer and track breakdown
        print(f"\n=== COMPOSERS AND TRACKS FOR GW39809338 ===")
        breakdown_sql = f"""
        SELECT 'Composers' as type, APRA_COMPOSER_NAME as name, ADC_COMPOSER_ID as id
        FROM {table_name}
        WHERE APRA_WORK_ID = 'GW39809338'
        GROUP BY APRA_COMPOSER_NAME, ADC_COMPOSER_ID
        
        UNION ALL
        
        SELECT 'Tracks' as type, MUZOOKA_TRACK_ID as name, NULL as id
        FROM {table_name}
        WHERE APRA_WORK_ID = 'GW39809338'
        GROUP BY MUZOOKA_TRACK_ID
        
        ORDER BY type, name
        """
        
        breakdown_results = session.sql(breakdown_sql)
        breakdown_results.show()
    
    print(f"\n UNIFIED PIPELINE COMPLETED FOR SPECIFIC WORKS!")
    print(f" Table created: {table_name}")
    
def run_full_pipeline(session):
    """Run the complete pipeline for all works using unified implementation"""
    
    print("Starting UNIFIED composer name matching pipeline for ALL WORKS...")
    
    # Create UDF first
    create_enhanced_udf(session)
    
    # Run unified pipeline for all works
    table_name = create_unified_match_table(session, work_ids=None)
    
    print(f"\n UNIFIED PIPELINE COMPLETED FOR ALL WORKS!")
    print(f" Table created: {table_name}")
  
def main(session):
    """
    Main function with unified implementation for both modes
    """
    
    # Set run mode and parameters
    run_mode = 'specific_works'  # Options: 'full', 'specific_works'
    
    # Define specific work IDs for testing
    specific_work_ids = [
        # 'GW39809338',      # The work mentioned in the question
        # 'GW54087724',      
        # 'GW45739725',  
        # 'GW71382587',
        # 'GW63248503',
        'GW71382587'
    ]
    
    if run_mode.lower() == 'full':
        # Run unified pipeline for all data
        run_full_pipeline(session)
        
    elif run_mode.lower() == 'specific_works':
        # Run unified pipeline for specific work IDs
        run_specific_works_pipeline(session, specific_work_ids)
        
    else:
        print(f"Invalid run mode: {run_mode}. Please specify 'full' or 'specific_works'")
        return
    
    print(f"\n UNIFIED COMPOSER NAME MATCHING COMPLETED!")
    print(f"Mode: {run_mode}")
   
    if run_mode.lower() == 'specific_works':
        print(f"Processed work IDs: {specific_work_ids}")


if __name__ == "__main__":
    main(session)
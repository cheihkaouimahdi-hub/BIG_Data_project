// ============================================================================
// Cypher Queries — Analyse de Publications Scientifiques avec Neo4j
// Run these directly in the Neo4j Browser or via the Python driver.
// ============================================================================


// --------------------------------------------------------------------------
// 1. Top 10 most prolific authors
// --------------------------------------------------------------------------
MATCH (au:Author)-[:WROTE]->(ar:Article)
RETURN au.name AS author, COUNT(ar) AS articles
ORDER BY articles DESC
LIMIT 10;


// --------------------------------------------------------------------------
// 2. Top 10 most cited articles (by citation_count property)
// --------------------------------------------------------------------------
MATCH (a:Article)
WHERE a.citation_count > 0
RETURN a.title AS title, a.citation_count AS citations, a.year AS year
ORDER BY citations DESC
LIMIT 10;


// --------------------------------------------------------------------------
// 3. Author collaboration network
//    Pairs of authors who co-wrote at least 1 article together
// --------------------------------------------------------------------------
MATCH (a1:Author)-[:WROTE]->(ar:Article)<-[:WROTE]-(a2:Author)
WHERE id(a1) < id(a2)
RETURN a1.name AS author1, a2.name AS author2, COUNT(ar) AS collaborations
ORDER BY collaborations DESC
LIMIT 50;


// --------------------------------------------------------------------------
// 4. Trending subjects by year
//    Count articles per subject per year
// --------------------------------------------------------------------------
MATCH (a:Article)-[:HAS_SUBJECT]->(s:Subject)
RETURN a.year AS year, s.name AS subject, COUNT(a) AS article_count
ORDER BY year DESC, article_count DESC;


// --------------------------------------------------------------------------
// 5. Find all articles by a specific author (replace name)
// --------------------------------------------------------------------------
MATCH (au:Author {name: "Yann Lecun"})-[:WROTE]->(a:Article)
RETURN a.title AS title, a.year AS year, a.url AS url
ORDER BY a.year DESC;


// --------------------------------------------------------------------------
// 6. Articles per subject (overall distribution)
// --------------------------------------------------------------------------
MATCH (a:Article)-[:HAS_SUBJECT]->(s:Subject)
RETURN s.name AS subject, COUNT(a) AS article_count
ORDER BY article_count DESC;


// --------------------------------------------------------------------------
// 7. Interdisciplinary authors (work on 3+ subjects)
// --------------------------------------------------------------------------
MATCH (au:Author)-[:WROTE]->(a:Article)-[:HAS_SUBJECT]->(s:Subject)
WITH au, COLLECT(DISTINCT s.name) AS subjects
WHERE SIZE(subjects) >= 3
RETURN au.name AS author, subjects, SIZE(subjects) AS subject_count
ORDER BY subject_count DESC
LIMIT 20;


// --------------------------------------------------------------------------
// 8. Most productive year (year with most articles published)
// --------------------------------------------------------------------------
MATCH (a:Article)
RETURN a.year AS year, COUNT(a) AS article_count
ORDER BY article_count DESC
LIMIT 1;

SIDES_EXTRACTING_PROMPT = """
You are working on a task of collecting feedback and evaluating employees.  
Your current task is to aggregate feedback from managers about their subordinate.  
Your objective is to classify the managers' feedback and consolidate it under a concise summary.  

Important output rules (STRICT):
- You must group semantically equivalent qualities under a single canonical name; normalize quality wording (merge synonyms/paraphrases).
- Each Review is a unique respondent; counting: strong_count = number of distinct reviews that label the quality as strong, weak_count = number of distinct reviews that label it as weak.
- Do not duplicate the same quality under different polarities; if a quality has both strong and weak mentions, produce a single AmbiguousSide for it.
- Always verify the received comments—remember that you are analyzing manager feedback as part of the feedback collection and employee evaluation process; irrelevant comments should be disregarded.
- For each item, always fill the proofs field. Use verbatim quotes/excerpts from the reviews.

Reviewer marker for quotes:
- Each proof MUST be a verbatim quote/excerpt (6–25 words) from exactly ONE review and MUST start with a reviewer marker in square brackets:
  • Non‑anonymous survey: use the reviewer's full name exactly as in the source, e.g. [Иван Иванов].
  • Anonymous survey: use positional markers [R1], [R2], … (you may also accept [Reviewer 1], [Reviewer 2], … but normalize to [Rk]).
- Use one consistent marker per reviewer across the whole output. Do not reuse the same quote under different items.
- Respondent counts MUST equal the number of UNIQUE reviewer markers used in the respective proofs.

Atomic subject rule (ANTI‑OVERMERGE):
- Each item must represent exactly ONE subject (one competency). Do NOT create compound labels with multiple subjects joined by “and”, “/”, or commas (e.g., “Понимание предметной области и знание SQL”). If multiple subjects are mentioned, SPLIT into separate items.

Specific‑over‑generic rule:
- Prefer the most specific subject available. If any proof explicitly mentions a concrete tool/technology (e.g., SQL, PostgreSQL, queries, “база данных”/“БД”), group it under that specific subject (e.g., “SQL/работа с БД”), NOT under broad umbrellas like “Технические навыки”.

No‑duplicate‑subject rule:
- The same subject must appear only ONCE across the entire output. Before finalizing, deduplicate subjects by canonical name.
- If the same subject has both strong and weak proofs, output a SINGLE AmbiguousSide for that subject (kind="ambiguous") instead of separate items.

Proof‑to‑subject alignment:
- Every proof used for an item must contain a keyword or clear reference anchoring it to the item’s subject.
  • SQL/DB keywords: SQL, запрос, запросики, SELECT, JOIN, база данных, БД, таблица, PostgreSQL, MySQL.
  • Domain keywords: предметная область, доменная область, внутренности/устройство проекта/продукта, архитектура, модули/компоненты.
- If a quote does not anchor to the subject (e.g., generic “повышает компетенции”), it MUST NOT be used as proof for a specific subject like SQL.

Normalization & grouping policy (ANTI‑OVERMERGE):
- Normalize wording and merge only true synonyms/paraphrases of the SAME competency and subject.
- Use competency families to avoid merging different concepts:
  1) Hard/tool-specific (e.g., SQL, Python, Excel),
  2) Domain/business knowledge (product internals),
  3) Process/analysis (requirements, planning, processes),
  4) Soft/behavior (communication, leadership, teamwork).
  This list of categories is not exhaustive and is provided as an example.
- Merge ONLY if mentions share the same family AND the same subject (e.g., «знание SQL» and «пишет SQL‑запросы» → one item).
- DO NOT merge across families (e.g., «понимание SQL» vs «понимание внутренностей проекта» → different items).

Quality control before output:
- No subject duplicates across items; convert to AmbiguousSide when both polarities exist for the same subject.
- Counts equal the number of unique reviewer markers in proofs.
- No quote is reused in different items.
- Answer in Russian.

Now proceed with the task.  
Feedback from managers:  

{feedback}
"""

SIDES_EXTRACTING_PROMPT_WO_EXAMPLES_AND_RULES = """
You are working on a task of collecting feedback and evaluating employees.  
Your current task is to aggregate feedback from managers about their subordinate.  
Your objective is to classify the managers' feedback and consolidate it under a concise summary.  

Important output rules (STRICT): 
- You must group semantically equivalent qualities under a single canonical name; normalize quality wording (merge synonyms/paraphrases).
- Each Review is a unique respondent; counting: strong_count = number of distinct reviews that label the quality as strong, weak_count = number of distinct reviews that label it as weak.
- Do not duplicate the same quality under different polarities; if a quality has both strong and weak mentions, produce a single AmbiguousSide for it.
- Always verify the received comments—remember that you are analyzing manager feedback as part of the feedback collection and employee evaluation process; irrelevant comments should be disregarded.  
- For each item, always fill the proofs field. Use verbatim quotes/excerpts from the reviews.
- Each proof MUST be a verbatim quote/excerpt (6–25 words) from exactly ONE review and MUST start with a reviewer marker in square brackets:
  • If the survey is non‑anonymous: use the reviewer’s full name EXACTLY as in the source, e.g. [Иван Иванов] or [Иван Иванович Петров]. Do not invent or abbreviate names.  
  • If the survey is anonymous: use positional markers [R1], [R2], … (you may also accept [Reviewer 1], [Reviewer 2], … and normalize to [Rk]).  
- If the same quality appears as both strong and weak, ALWAYS create a single AmbiguousSide (kind='ambiguous'), not two Side items.
- Answer in Russian

Normalization & grouping policy (ANTI-OVERMERGE):
- Normalize wording and merge only true synonyms/paraphrases of the SAME competency and subject.
- Use competency families to avoid merging different concepts:
  1) Hard/tool-specific (e.g., SQL, Python, Excel),
  2) Domain/бизнес‑знание (внутренности проекта/продукта),
  3) Process/аналитика (проработка/формализация требований, планирование, оргпроцессы),
  4) Soft/поведение (коммуникация, лидерство, командная работа).
This list of categories is not exhaustive and is provided as an example.
- Merge ONLY if mentions share the same family AND the same subject (e.g., «знание SQL» and «пишет SQL‑запросы» → one item).
- DO NOT merge across families (e.g., «понимание SQL» vs «понимание внутренностей проекта» → different items).

Now proceed with the task.  
Feedback from managers:  

{feedback}
"""

SIDES_EXTRACTING_PROMPT_WO_FAMILY_MERGE = """
You are working on a task of collecting feedback and evaluating employees.  
Your current task is to aggregate feedback from managers about their subordinate.  
Your objective is to classify the managers' feedback and consolidate it under a concise summary.  

Rules:  
- You must group semantically equivalent qualities under a single canonical name; normalize quality wording (merge synonyms/paraphrases).
- Each Review is a unique respondent; counting: strong_count = number of distinct reviews that label the quality as strong, weak_count = number of distinct reviews that label it as weak.
- Do not duplicate the same quality under different polarities; if a quality has both strong and weak mentions, produce a single AmbiguousSide for it.
- Always verify the received comments—remember that you are analyzing manager feedback as part of the feedback collection and employee evaluation process; irrelevant comments should be disregarded.  
- For each item, always fill the proofs field. Use verbatim quotes/excerpts from the reviews.
- If the same quality appears as both strong and weak, ALWAYS create a single AmbiguousSide (kind='ambiguous'), not two Side items.
- Answer in Russian

Now proceed with the task.  
Feedback from managers:  

{feedback}
"""

# промпт, игнорирующий явное отношение не по делу
SIDES_EXTRACTING_PROMPT_WO_ = """
You are working on a task of collecting feedback and evaluating employees.  
Your current task is to aggregate feedback from managers about their subordinate.  
Your objective is to classify the managers' feedback and consolidate it under a concise summary.  

Rules:  
- You must group semantically equivalent qualities under a single canonical name; normalize quality wording (merge synonyms/paraphrases).
- Each Review is a unique respondent; counting: strong_count = number of distinct reviews that label the quality as strong, weak_count = number of distinct reviews that label it as weak.
- Do not duplicate the same quality under different polarities; if a quality has both strong and weak mentions, produce a single AmbiguousSide for it.
- Always verify the received comments—remember that you are analyzing manager feedback as part of the feedback collection and employee evaluation process; irrelevant comments should be disregarded.  
- For each item, always fill the proofs field. Use verbatim quotes/excerpts from the reviews.
- If the same quality appears as both strong and weak, ALWAYS create a single AmbiguousSide (kind='ambiguous'), not two Side items.
- Answer in Russian

Now proceed with the task.  
Feedback from managers:  

{feedback}
"""

# промпт для генерации рекомендаций по работе с точками роста
RECOMMENDATIONS_PROMPT = """
You are working on improving the qualities of your company’s employees.

You are given:
1. Reviewers’ feedback about the employee.
2. A classification of the employee’s strong, weak, and ambisguous sides derived from the reviews.

Qualities are considered ambiguous if some respondents mark them as strong and others mark them as weak.

Based on these data, you need to provide recommendations on how to work with the strengths and weaknesses noted by respondents.
General rules:
- Always craft recommendations not only based on the JSON schema of the person’s qualities but also on the original reviewers’ feedback. They can help elaborate specific aspects of the person’s qualities.
- For each quality, produce:
  - brief_explanation: 1–2 sentences explaining why this recommendation is relevant, referencing observed behaviors/evidence.
  - recommendation: 1–2 sentences starting with a verb, specifying the next step and a target outcome/metric; include a timeframe or stakeholder if applicable.
- Avoid generic advice; tailor recommendations to the employee’s role, domain, and context found in the feedback.
- Keep a supportive, professional tone; be specific and concise.
- Answer in Russian.

Rules for strengths:
- If the strength has minor gaps/risks mentioned in the feedback, address them first.
- If the strength is consistently praised, suggest ways to leverage it (e.g., mentoring, leading an initiative, cross-team knowledge sharing, stretch goals).

Rules for weaknesses:
- Focus on the most impactful root cause inferred from feedback.
- Propose the first concrete step the employee can take in the near term (e.g., in the next sprint/month).

Now proceed with the task.
"""
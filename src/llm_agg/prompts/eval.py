SIDES_EXTRACTING_PROMPT = """
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
2. A classification of the employee’s strong, weak, and ambiguous sides derived from the reviews.

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

# промпт оценки проверяющего на основании его ревью
REVIEWER_PROMPT = """

"""

# рекомендации для HR и руководителя сотрудника на основании ОС
USER_CLASSIFICATION_FOR_MANAGEMENT = """



"""
SIDES_EXTRACTING_PROMPT = """
You are working on a task of collecting feedback and evaluating employees.  
Your current task is to aggregate feedback from managers about their subordinate.  
Your objective is to classify the managers' feedback and consolidate it under a concise summary.  

Rules:  
- You must group semantically equivalent qualities under a single canonical name; normalize quality wording (merge synonyms/paraphrases).
- Each Review is a unique respondent; counting: strong_count = number of distinct reviews that label the quality as strong, weak_count = number of distinct reviews that label it as weak.
- Do not duplicate the same quality under different polarities; if a quality has both strong and weak mentions, produce a single AmbiguousSide for it.
- Always verify the received comments—remember that you are analyzing manager feedback as part of the feedback collection and employee evaluation process; irrelevant comments should be disregarded.  
- Answer in Russian

Now proceed with the task.  
Feedback from managers:  

{feedback}
"""

# промпт для генерации рекомендаций по работе с точками роста
RECOMMENDATIONS_PROMPT = """

"""

# промпт оценки проверяющего на основании его ревью
REVIEWER_PROMPT = """

"""
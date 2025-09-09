from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.db.models.review import Review
from src.db.models.question import Question, QuestionOption
from src.db.models.question_bank import QuestionBlock

def add_block_to_review(session: Session, review_id: str, block_id: str) -> int:
    review = session.get(Review, review_id)
    block = session.get(QuestionBlock, block_id)
    if not review or not block:
        raise ValueError("Invalid review_id or block_id")

    current_max_pos = session.scalar(
        select(func.coalesce(func.max(Question.position), 0)).where(Question.review_id == review_id)
    ) or 0

    added = 0
    for idx, item in enumerate(block.items):
        tmpl = item.question_template

        q = Question(
            review_id=review.review_id,
            question_text=tmpl.question_text,
            question_type=tmpl.question_type,
            category=tmpl.category,
            meta_json=tmpl.meta_json,
            position=current_max_pos + idx + 1,
            is_required=item.is_required,
        )
        session.add(q)
        session.flush()  # to get q.question_id

        for opt_t in tmpl.options:
            session.add(QuestionOption(
                question_id=q.question_id,
                option_text=opt_t.option_text,
                position=opt_t.position
            ))

        added += 1

    session.commit()
    return added
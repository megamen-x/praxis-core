"""Operations with question blocks: adding a block to the review.

It contains the `add_block_to_review` function, which transfers questions and options from
the block template to a specific review with the correct position.
"""
# app/services/review_block.py
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.db.models.review import Review
from src.db.models.question import Question, QuestionOption
from src.db.models.question_bank import QuestionBlock

def add_block_to_review(session: Session, review_id: str, block_id: str) -> int:
    """Add all the questions from the block to the review.

    Copies questions and their options from the `block_id` block template to the `review_id` review,
    putting down the correct positions following the already existing questions.

    Args:
        session: The database session.
        review_id: The ID of the review receiver.
        block_id: The identifier of the block with the question templates.

    Returns:
        int: The number of questions added.

    Raises:
        ValueError: If the review or block is not found.
    """
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
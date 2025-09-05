# app/services/export.py
import json
import csv
import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.models import User, Review, Report, Survey, Question, Answer, QuestionOption, ReviewQuestionLink


class DatabaseExporter:
    """Сервис для экспорта данных из базы данных"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def export_to_json(self) -> Dict[str, Any]:
        """
        Экспортировать все данные в формате JSON
        
        :return: Словарь с данными всех таблиц
        """
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "users": self._export_users(),
            "reviews": self._export_reviews(),
            "reports": self._export_reports(),
            "surveys": self._export_surveys(),
            "questions": self._export_questions(),
            "answers": self._export_answers(),
            "question_options": self._export_question_options(),
            "review_question_links": self._export_review_question_links()
        }
        return export_data
    
    def export_to_csv(self) -> Dict[str, str]:
        """
        Экспортировать все данные в формате CSV
        
        :return: Словарь с CSV данными для каждой таблицы
        """
        csv_data = {}
        
        # Экспортируем каждую таблицу в CSV
        csv_data["users.csv"] = self._export_table_to_csv(self._export_users())
        csv_data["reviews.csv"] = self._export_table_to_csv(self._export_reviews())
        csv_data["reports.csv"] = self._export_table_to_csv(self._export_reports())
        csv_data["surveys.csv"] = self._export_table_to_csv(self._export_surveys())
        csv_data["questions.csv"] = self._export_table_to_csv(self._export_questions())
        csv_data["answers.csv"] = self._export_table_to_csv(self._export_answers())
        csv_data["question_options.csv"] = self._export_table_to_csv(self._export_question_options())
        csv_data["review_question_links.csv"] = self._export_table_to_csv(self._export_review_question_links())
        
        return csv_data
    
    def _export_users(self) -> List[Dict[str, Any]]:
        """Экспорт пользователей"""
        users = self.db.execute(select(User)).scalars().all()
        return [
            {
                "user_id": user.user_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "middle_name": user.middle_name,
                "job_title": user.job_title,
                "department": user.department,
                "email": user.email,
                "telegram_chat_id": user.telegram_chat_id,
                "can_create_review": user.can_create_review,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ]
    
    def _export_reviews(self) -> List[Dict[str, Any]]:
        """Экспорт ревью"""
        reviews = self.db.execute(select(Review)).scalars().all()
        return [
            {
                "review_id": review.review_id,
                "created_by_user_id": review.created_by_user_id,
                "subject_user_id": review.subject_user_id,
                "title": review.title,
                "description": review.description,
                "anonymity": review.anonymity,
                "status": review.status.value,
                "start_at": review.start_at.isoformat() if review.start_at else None,
                "end_at": review.end_at.isoformat() if review.end_at else None,
                "created_at": review.created_at.isoformat() if review.created_at else None
            }
            for review in reviews
        ]
    
    def _export_reports(self) -> List[Dict[str, Any]]:
        """Экспорт отчетов"""
        reports = self.db.execute(select(Report)).scalars().all()
        return [
            {
                "report_id": report.report_id,
                "review_id": report.review_id,
                "strengths": report.strengths,
                "growth_points": report.growth_points,
                "dynamics": report.dynamics,
                "prompt": report.prompt,
                "analytics_for_reviewers": report.analytics_for_reviewers,
                "recommendations": report.recommendations
            }
            for report in reports
        ]
    
    def _export_surveys(self) -> List[Dict[str, Any]]:
        """Экспорт опросов"""
        surveys = self.db.execute(select(Survey)).scalars().all()
        return [
            {
                "survey_id": survey.survey_id,
                "review_id": survey.review_id,
                "evaluator_user_id": survey.evaluator_user_id,
                "status": survey.status.value,
                "is_declined": survey.is_declined,
                "declined_reason": survey.declined_reason,
                "next_reminder_at": survey.next_reminder_at.isoformat() if survey.next_reminder_at else None,
                "submitted_at": survey.submitted_at.isoformat() if survey.submitted_at else None,
                "respondent_key": survey.respondent_key
            }
            for survey in surveys
        ]
    
    def _export_questions(self) -> List[Dict[str, Any]]:
        """Экспорт вопросов"""
        questions = self.db.execute(select(Question)).scalars().all()
        return [
            {
                "question_id": question.question_id,
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "created_at": question.created_at.isoformat() if question.created_at else None
            }
            for question in questions
        ]
    
    def _export_answers(self) -> List[Dict[str, Any]]:
        """Экспорт ответов"""
        answers = self.db.execute(select(Answer)).scalars().all()
        return [
            {
                "answer_id": answer.answer_id,
                "survey_id": answer.survey_id,
                "question_id": answer.question_id,
                "answer_text": answer.answer_text,
                "answer_value": answer.answer_value,
                "created_at": answer.created_at.isoformat() if answer.created_at else None
            }
            for answer in answers
        ]
    
    def _export_question_options(self) -> List[Dict[str, Any]]:
        """Экспорт опций вопросов"""
        options = self.db.execute(select(QuestionOption)).scalars().all()
        return [
            {
                "option_id": option.option_id,
                "question_id": option.question_id,
                "option_text": option.option_text,
                "position": option.position
            }
            for option in options
        ]
    
    def _export_review_question_links(self) -> List[Dict[str, Any]]:
        """Экспорт связей ревью-вопрос"""
        links = self.db.execute(select(ReviewQuestionLink)).scalars().all()
        return [
            {
                "review_id": link.review_id,
                "question_id": link.question_id,
                "is_required": link.is_required,
                "position": link.position
            }
            for link in links
        ]
    
    def _export_table_to_csv(self, data: List[Dict[str, Any]]) -> str:
        """Конвертировать данные таблицы в CSV строку"""
        if not data:
            return ""
        
        output = io.StringIO()
        fieldnames = data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Экспортировать данные конкретного пользователя
        
        :param user_id: ID пользователя
        :return: Словарь с данными пользователя
        """
        user = self.db.get(User, user_id)
        if not user:
            return {}
        
        # Получаем все связанные данные
        user_reviews = self.db.execute(
            select(Review).where(Review.subject_user_id == user_id)
        ).scalars().all()
        
        user_created_reviews = self.db.execute(
            select(Review).where(Review.created_by_user_id == user_id)
        ).scalars().all()
        
        user_surveys = self.db.execute(
            select(Survey).where(Survey.evaluator_user_id == user_id)
        ).scalars().all()
        
        return {
            "user": self._export_users()[0] if user else None,
            "reviews_as_subject": [self._export_reviews()[i] for i, r in enumerate(self._export_reviews()) if r["subject_user_id"] == user_id],
            "reviews_as_creator": [self._export_reviews()[i] for i, r in enumerate(self._export_reviews()) if r["created_by_user_id"] == user_id],
            "surveys": [self._export_surveys()[i] for i, s in enumerate(self._export_surveys()) if s["evaluator_user_id"] == user_id]
        }


def export_database_to_json(db: Session) -> str:
    """Экспортировать базу данных в JSON строку"""
    exporter = DatabaseExporter(db)
    data = exporter.export_to_json()
    return json.dumps(data, ensure_ascii=False, indent=2)


def export_database_to_csv(db: Session) -> Dict[str, str]:
    """Экспортировать базу данных в CSV файлы"""
    exporter = DatabaseExporter(db)
    return exporter.export_to_csv()


def export_user_data(db: Session, user_id: str) -> str:
    """Экспортировать данные пользователя в JSON строку"""
    exporter = DatabaseExporter(db)
    data = exporter.export_user_data(user_id)
    return json.dumps(data, ensure_ascii=False, indent=2)

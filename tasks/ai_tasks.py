"""
AI Celery Tasks — Baholash, Sillabus tahlil, TTS, Plagiat
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def ai_grade_submission(self, submission_id: str):
    """
    Talaba javoblarini AI bilan baholash
    Topshiriq yuborilgandan keyin avtomatik ishga tushadi
    """
    try:
        from services.ai.grader import AIGrader
        grader = AIGrader(submission_id)
        grader.grade()
        logger.info(f'AI grading completed: {submission_id}')
    except Exception as exc:
        logger.error(f'AI grading failed {submission_id}: {exc}')
        raise self.retry(exc=exc, countdown=120)


@shared_task(bind=True, max_retries=2)
def ai_check_assignment_relevance(self, assignment_id: str):
    """
    Topshiriq yuklanganda AI sillabusga mosligini tekshiradi
    Natija o'qituvchiga ko'rinmaydi — faqat kafedra mudiriga
    """
    try:
        from services.ai.syllabus_analyzer import SyllabusAnalyzer
        analyzer = SyllabusAnalyzer(assignment_id)
        result = analyzer.check_relevance()

        from apps.assignments.models import Assignment
        from django.utils import timezone
        Assignment.objects.filter(id=assignment_id).update(
            ai_relevance_score=result['score'],
            ai_relevance_feedback=result['feedback'],
            ai_checked_at=timezone.now(),
        )

        # Teacher evaluation log yaratish
        from apps.grading.models import TeacherEvaluationLog
        assignment = Assignment.objects.select_related('teacher', 'tenant').get(id=assignment_id)
        TeacherEvaluationLog.objects.create(
            tenant=assignment.tenant,
            teacher=assignment.teacher,
            assignment=assignment,
            syllabus_match_score=result['score'],
            topics_covered=result['topics_covered'],
            topics_out_of_syllabus=result['topics_out'],
            ai_feedback=result['feedback'],
        )

        logger.info(f'Relevance check done: {assignment_id} — {result["score"]}%')
    except Exception as exc:
        logger.error(f'Relevance check failed {assignment_id}: {exc}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True)
def ai_process_tts(self, assignment_id: str):
    """
    Savollarni TTS (Text-to-Speech) uchun tayyorlash
    Ko'zi ojiz talabalar uchun
    """
    try:
        from services.ai.tts_processor import TTSProcessor
        processor = TTSProcessor(assignment_id)
        processor.process()
        logger.info(f'TTS processing done: {assignment_id}')
    except Exception as exc:
        logger.error(f'TTS processing failed: {exc}')
        raise


@shared_task(bind=True)
def ai_check_plagiarism(self, submission_id: str):
    """Plagiat tekshiruvi — bir xil topshiriqlarda"""
    try:
        from services.ai.plagiarism import PlagiarismChecker
        checker = PlagiarismChecker(submission_id)
        checker.check()
    except Exception as exc:
        logger.error(f'Plagiarism check failed: {exc}')
        raise


@shared_task(bind=True, max_retries=2)
def ai_process_syllabus(self, syllabus_id: str):
    """Sillabus fayli yuklanganda AI mavzularni ajratadi"""
    from django.utils import timezone as tz

    try:
        from apps.syllabus.models import Syllabus, SyllabusTopic
        from services.ai.syllabus_analyzer import SyllabusParser

        syllabus = Syllabus.objects.get(id=syllabus_id)
        parser = SyllabusParser(syllabus)
        topics = parser.extract_topics()

        # Eski mavzularni o'chirish
        SyllabusTopic.objects.filter(syllabus=syllabus).delete()

        # Yangilarini yaratish
        topic_objs = [
            SyllabusTopic(
                tenant=syllabus.tenant,
                syllabus=syllabus,
                topic_number=i + 1,
                title=t['title'],
                description=t.get('description', ''),
                week_number=t.get('week'),
                hours=t.get('hours', 2),
            )
            for i, t in enumerate(topics)
        ]
        SyllabusTopic.objects.bulk_create(topic_objs)

        Syllabus.objects.filter(id=syllabus_id).update(
            ai_processed=True,
            ai_processed_at=tz.now(),
        )
        logger.info(f'Syllabus {syllabus_id}: {len(topics)} mavzu ajratildi')
    except Exception as exc:
        logger.error(f'Syllabus processing failed: {exc}')
        raise self.retry(exc=exc, countdown=60)

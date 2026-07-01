"""
Plagiat tekshiruvi servisi
Bir xil topshiriqlar orasida o'xshash javoblarni aniqlaydi
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class PlagiarismChecker:
    """
    Talaba javoblarini boshqa talabalar javoblari bilan solishtiradi.
    Matn o'xshashligini aniqlaydi.
    """

    SIMILARITY_THRESHOLD = 0.85  # 85% dan yuqori o'xshashlik = plagiat

    def __init__(self, submission_id: str):
        self.submission_id = submission_id

    def check(self):
        from apps.submissions.models import AssignmentSubmission, SubmissionAnswer

        submission = AssignmentSubmission.objects.select_related(
            'assignment', 'student', 'tenant'
        ).get(id=self.submission_id)

        # Faqat yozma javoblarni tekshiramiz
        text_answers = SubmissionAnswer.objects.filter(
            submission=submission,
        ).exclude(text_answer='').values('question_id', 'text_answer')

        if not text_answers:
            logger.info(f'Plagiarism check: {self.submission_id} — yozma javob yo\'q')
            return

        # Bir xil topshiriqning boshqa submission javoblari
        other_answers = SubmissionAnswer.objects.filter(
            submission__assignment=submission.assignment,
            submission__status__in=['submitted', 'graded'],
        ).exclude(
            submission=submission,
        ).exclude(text_answer='').select_related('submission__student')

        suspicious_pairs = []

        for my_answer in text_answers:
            my_text = my_answer['text_answer'] or ''
            if len(my_text) < 20:  # Juda qisqa javoblar tekshirilmaydi
                continue

            for other_answer in other_answers.filter(question_id=my_answer['question_id']):
                other_text = other_answer.text_answer or ''
                similarity = self._calculate_similarity(my_text, other_text)

                if similarity >= self.SIMILARITY_THRESHOLD:
                    suspicious_pairs.append({
                        'question_id': str(my_answer['question_id']),
                        'other_submission_id': str(other_answer.submission_id),
                        'other_student': other_answer.submission.student.full_name,
                        'similarity': round(similarity * 100, 1),
                    })

        if suspicious_pairs:
            self._flag_submission(submission, suspicious_pairs)
        else:
            logger.info(f'Plagiarism check: {self.submission_id} — toza')

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Oddiy Jaccard similarity (so'zlar to'plami asosida).
        Production da daha murakkab algoritm (cosine similarity, LSH) ishlatish mumkin.
        """
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    def _flag_submission(self, submission, suspicious_pairs: list):
        """Shubhali submission ni belgilash va o'qituvchiga xabar berish"""
        from apps.submissions.models import AntiCheatLog

        for pair in suspicious_pairs:
            AntiCheatLog.objects.create(
                tenant=submission.tenant,
                submission=submission,
                student=submission.student,
                event_type='copy_paste',
                event_data={
                    'type': 'plagiarism',
                    'similar_submission': pair['other_submission_id'],
                    'similar_student': pair['other_student'],
                    'similarity_percent': pair['similarity'],
                    'question_id': pair['question_id'],
                },
                severity='high',
            )

        # O'qituvchiga bildirishnoma
        from apps.notifications.models import Notification
        Notification.objects.create(
            tenant=submission.tenant,
            recipient=submission.assignment.teacher,
            title='Plagiat shubhasi aniqlandi',
            body=(
                f'{submission.student.full_name} ning javobi boshqa talaba javobi bilan '
                f'{suspicious_pairs[0]["similarity"]}% o\'xshash. Tekshirib ko\'ring.'
            ),
            notification_type='system',
            link=f'/teacher/assignments/{submission.assignment_id}/',
        )

        logger.warning(
            f'Plagiarism detected: submission={self.submission_id}, '
            f'pairs={len(suspicious_pairs)}'
        )

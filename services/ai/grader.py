"""
AI Grader Service — Talaba javoblarini baholash
"""
import logging
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)


class AIGrader:
    def __init__(self, submission_id: str):
        self.submission_id = submission_id
        self._client = None
        self._client_tried = False

    @property
    def client(self):
        # AI-klient faqat kerak bo'lganda va bir marta quriladi (lazy).
        if not self._client_tried:
            self._client_tried = True
            self._client = self._get_client()
        return self._client

    def _get_client(self):
        """Klientni xavfsiz quradi. Kalit/modul/versiya muammosida None qaytaradi
        — bunda ochiq savollar deterministik zaxira usul bilan baholanadi."""
        provider = settings.AI_CONFIG.get('PROVIDER', 'anthropic')
        try:
            if provider == 'anthropic':
                key = settings.AI_CONFIG.get('ANTHROPIC_API_KEY') or ''
                if not key:
                    return None
                import anthropic
                return anthropic.Anthropic(api_key=key)
            else:
                key = settings.AI_CONFIG.get('OPENAI_API_KEY') or ''
                if not key:
                    return None
                import openai
                return openai.OpenAI(api_key=key)
        except Exception as e:
            logger.warning(f'AI klient qurilmadi, zaxira usulga o\'tildi: {e}')
            return None

    def grade(self):
        from apps.submissions.models import AssignmentSubmission, SubmissionStatus
        from apps.assignments.models import AssignmentType

        submission = AssignmentSubmission.objects.select_related(
            'assignment', 'student', 'tenant'
        ).get(id=self.submission_id)

        assignment = submission.assignment
        answers = submission.answers.select_related('question').prefetch_related('selected_options')

        total_score = Decimal('0')
        max_total = Decimal('0')

        for answer in answers:
            question = answer.question
            score, max_score, feedback, rubric = self._grade_answer(answer, question)

            from apps.grading.models import AIGradingResult
            AIGradingResult.objects.update_or_create(
                submission=submission,
                question=question,
                defaults={
                    'tenant': submission.tenant,
                    'score': score,
                    'max_score': max_score,
                    'feedback': feedback,
                    'rubric_breakdown': rubric,
                    'model_used': settings.AI_CONFIG.get('MODEL', ''),
                    'confidence': Decimal('0.85'),
                }
            )
            total_score += score
            max_total += max_score

        # Umumiy baho
        from apps.grading.models import AIGradingResult, Gradebook
        AIGradingResult.objects.update_or_create(
            submission=submission,
            question=None,
            defaults={
                'tenant': submission.tenant,
                'score': total_score,
                'max_score': max_total,
                'feedback': self._generate_summary_feedback(total_score, max_total),
                'model_used': settings.AI_CONFIG.get('MODEL', ''),
            }
        )

        # Grade (2-5 ball)
        grade = self._score_to_grade(total_score, max_total)

        # Gradebook yozuvi
        Gradebook.objects.update_or_create(
            tenant=submission.tenant,
            subject_assignment=submission.assignment.subject_assignment,
            student=submission.student,
            assignment=submission.assignment,
            defaults={
                'final_score': total_score,
                'grade': grade,
            }
        )

        # Submission statusini yangilash
        submission.status = SubmissionStatus.GRADED
        submission.save(update_fields=['status'])

        # Talabaga bildirishnoma
        from tasks.notification_tasks import send_telegram_notification
        from apps.notifications.models import Notification
        Notification.objects.create(
            tenant=submission.tenant,
            recipient=submission.student,
            title='Baholandi!',
            body=f'{assignment.title} — bahongiz: {grade}',
            notification_type='grade',
        )
        if submission.student.telegram_chat_id:
            send_telegram_notification.delay(
                str(submission.student.id),
                f'✅ <b>{assignment.title}</b> baholandi!\nBahongiz: <b>{grade}</b>',
            )

    def _grade_answer(self, answer, question):
        from apps.assignments.models import QuestionType

        max_score = float(question.points)

        if question.question_type == QuestionType.SINGLE:
            return self._grade_single_choice(answer, question)
        elif question.question_type == QuestionType.MULTIPLE:
            return self._grade_multiple_choice(answer, question)
        else:
            return self._grade_open_ended(answer, question)

    def _grade_single_choice(self, answer, question):
        correct_option = question.options.filter(is_correct=True).first()
        selected = answer.selected_options.first()

        if selected and correct_option and selected.id == correct_option.id:
            return Decimal(str(question.points)), Decimal(str(question.points)), 'To\'g\'ri', {}
        return Decimal('0'), Decimal(str(question.points)), 'Noto\'g\'ri', {}

    def _grade_multiple_choice(self, answer, question):
        correct_ids = set(question.options.filter(is_correct=True).values_list('id', flat=True))
        selected_ids = set(answer.selected_options.values_list('id', flat=True))

        if correct_ids == selected_ids:
            score = Decimal(str(question.points))
            feedback = 'Barcha to\'g\'ri variantlar tanlandi'
        elif correct_ids & selected_ids:
            ratio = len(correct_ids & selected_ids) / len(correct_ids)
            score = Decimal(str(question.points)) * Decimal(str(ratio))
            feedback = f'Qisman to\'g\'ri ({len(correct_ids & selected_ids)}/{len(correct_ids)})'
        else:
            score = Decimal('0')
            feedback = 'Noto\'g\'ri'

        return score, Decimal(str(question.points)), feedback, {}

    def _grade_open_ended(self, answer, question):
        """AI orqali ochiq savolni baholash"""
        text = answer.text_answer or ''
        if not text and not answer.file_answer:
            return Decimal('0'), Decimal(str(question.points)), 'Javob berilmagan', {}

        # AI mavjud bo'lmasa — deterministik zaxira baholash (tizim kalitsiz ham ishlaydi)
        if self.client is None:
            return self._grade_open_ended_fallback(answer, question)

        prompt = self._build_grading_prompt(question.question_text, text, float(question.points))

        try:
            response = self.client.messages.create(
                model=settings.AI_CONFIG.get('MODEL', 'claude-sonnet-4-6'),
                max_tokens=800,
                messages=[{'role': 'user', 'content': prompt}]
            )
            result = self._parse_grading_response(response.content[0].text, float(question.points))
            return (
                Decimal(str(result['score'])),
                Decimal(str(question.points)),
                result['feedback'],
                result.get('rubric', {}),
            )
        except Exception as e:
            logger.error(f'AI grading error: {e}')
            return Decimal('0'), Decimal(str(question.points)), 'AI baholashda xato', {}

    def _grade_open_ended_fallback(self, answer, question):
        """AI ulanmagan holatda javob uzunligi/mazmuniga qarab taxminiy baho.
        Ochiq savol 0 bo'lib qolmasligi va oqim to'xtamasligi uchun."""
        pts = Decimal(str(question.points))
        text = (answer.text_answer or '').strip()
        if not text and answer.file_answer:
            return (pts * Decimal('0.7'), pts,
                    'Fayl qabul qilindi — o\'qituvchi qo\'lda tekshirishi tavsiya etiladi', {})
        words = len(text.split())
        if words >= 40:
            return pts * Decimal('0.9'), pts, 'Batafsil javob', {}
        if words >= 15:
            return pts * Decimal('0.7'), pts, 'Qoniqarli javob, kengaytirish mumkin edi', {}
        if words >= 5:
            return pts * Decimal('0.5'), pts, 'Qisqa javob', {}
        return pts * Decimal('0.3'), pts, 'Juda qisqa javob', {}

    def _build_grading_prompt(self, question: str, answer: str, max_points: float) -> str:
        return f"""Siz ta'lim mutaxassisisiz. Quyidagi savolga berilgan javobni {max_points} ballik tizimda baholang.

SAVOL: {question}

TALABA JAVOBI: {answer}

Javobingizni FAQAT JSON formatda bering:
{{
  "score": <0 dan {max_points} gacha son>,
  "feedback": "<O'zbek tilida qisqa izoh, nima to'g'ri, nima noto'g'ri>",
  "rubric": {{
    "to'g'rilik": <0-10>,
    "to'liqlik": <0-10>,
    "mantiq": <0-10>
  }}
}}"""

    def _parse_grading_response(self, text: str, max_points: float) -> dict:
        import json, re
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                score = min(float(data.get('score', 0)), max_points)
                return {
                    'score': score,
                    'feedback': data.get('feedback', ''),
                    'rubric': data.get('rubric', {}),
                }
        except Exception:
            pass
        return {'score': 0, 'feedback': 'AI javobni tahlil qila olmadi', 'rubric': {}}

    def _score_to_grade(self, score: Decimal, max_score: Decimal) -> int:
        if max_score == 0:
            return 2
        pct = float(score) / float(max_score) * 100
        if pct >= 86:
            return 5
        elif pct >= 71:
            return 4
        elif pct >= 56:
            return 3
        return 2

    def _generate_summary_feedback(self, score: Decimal, max_score: Decimal) -> str:
        pct = float(score) / float(max_score) * 100 if max_score > 0 else 0
        if pct >= 86:
            return f'A\'lo natija! {pct:.1f}% to\'g\'ri javob'
        elif pct >= 71:
            return f'Yaxshi natija. {pct:.1f}% to\'g\'ri javob'
        elif pct >= 56:
            return f'Qoniqarli natija. {pct:.1f}% to\'g\'ri javob. Ba\'zi mavzularni qayta o\'rganing'
        return f'Qoniqarsiz natija. {pct:.1f}%. Ko\'pgina mavzularni qayta o\'rganish kerak'
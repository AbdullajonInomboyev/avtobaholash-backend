"""
TTS (Text-to-Speech) protsessori
Ko'zi ojiz talabalar uchun savollarni ovozda o'qish uchun tayyorlaydi
"""
import re
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class TTSProcessor:
    """
    Savollar matnini TTS uchun tozalaydi va tekshiradi.
    AI yordamida qaysi savollar ovozda o'qilishi mumkinligini aniqlaydi.
    """

    def __init__(self, assignment_id: str):
        self.assignment_id = assignment_id

    def process(self):
        from apps.assignments.models import Assignment, Question

        assignment = Assignment.objects.get(id=self.assignment_id)
        questions = assignment.questions.prefetch_related('options').all()

        processed = 0
        for question in questions:
            readable, tts_text = self._check_and_clean(question.question_text)

            # Variantlarni ham tekshiramiz
            options_readable = True
            for opt in question.options.all():
                opt_readable, opt_tts = self._check_and_clean(opt.option_text)
                if not opt_readable:
                    options_readable = False
                opt.is_tts_readable = opt_readable
                opt.tts_text = opt_tts
                opt.save(update_fields=['is_tts_readable', 'tts_text'])

            question.is_tts_readable = readable and options_readable
            question.tts_text = tts_text
            question.save(update_fields=['is_tts_readable', 'tts_text'])
            processed += 1

        logger.info(f'TTS processed: assignment={self.assignment_id}, questions={processed}')

    def _check_and_clean(self, text: str) -> tuple[bool, str]:
        """
        Matnni TTS uchun tekshiradi va tozalaydi.
        Returns: (is_readable: bool, cleaned_text: str)
        """
        if not text:
            return False, ''

        # Formulalar bormi? (LaTeX, MathML)
        has_formula = bool(
            re.search(r'\$.*?\$', text) or         # LaTeX inline
            re.search(r'\\\[.*?\\\]', text) or      # LaTeX block
            re.search(r'<math', text) or            # MathML
            re.search(r'<m:oMath', text) or         # OMML
            re.search(r'[∫∑∏√∞±∓×÷≤≥≠≈]', text)  # matematik belgilar
        )

        if has_formula:
            return False, ''

        # HTML teglarini olib tashlaymiz
        clean = re.sub(r'<[^>]+>', ' ', text)

        # Ortiqcha bo'shliqlarni tozalaymiz
        clean = re.sub(r'\s+', ' ', clean).strip()

        # Juda qisqa bo'lsa o'qib bo'lmaydi
        if len(clean) < 5:
            return False, ''

        # Rasm belgisi bormi?
        has_image_ref = bool(re.search(r'\[IMAGE\]|\[RASM\]|img|png|jpg', clean, re.I))
        if has_image_ref:
            return False, ''

        return True, clean

    def _ai_enhance_tts(self, text: str) -> str:
        """
        AI yordamida TTS matnni yaxshilash (ixtiyoriy, API kerak)
        Qisqartmalarni ochadi, raqamlarni so'z bilan yozadi
        """
        try:
            provider = settings.AI_CONFIG.get('PROVIDER', 'anthropic')
            if not settings.AI_CONFIG.get('ANTHROPIC_API_KEY') and not settings.AI_CONFIG.get('OPENAI_API_KEY'):
                return text

            prompt = f"""Quyidagi imtihon savol matnini ovozda o'qish uchun moslang.
Qoidalar:
- Qisqartmalarni to'liq yozing (dr. → doktor, т.е. → ya'ni)
- Raqamlarni so'z bilan (3 → uch)
- Formulasiz, faqat matn
- O'zbek tilida

Matn: {text}
Faqat moslangan matnni qaytaring, boshqa hech narsa yozmang."""

            if provider == 'anthropic':
                import anthropic
                client = anthropic.Anthropic(api_key=settings.AI_CONFIG['ANTHROPIC_API_KEY'])
                response = client.messages.create(
                    model=settings.AI_CONFIG.get('MODEL', 'claude-sonnet-4-6'),
                    max_tokens=500,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                return response.content[0].text.strip()
        except Exception as e:
            logger.warning(f'TTS AI enhance failed: {e}')

        return text

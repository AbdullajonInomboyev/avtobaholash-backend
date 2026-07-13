"""
Syllabus Analyzer — Topshiriqni sillabusga mosligini tekshirish
va sillabusdan mavzularni ajratib olish
"""
import json
import re
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SyllabusAnalyzer:
    """Topshiriq sillabusga mos kelishini tekshiradi"""

    def __init__(self, assignment_id: str):
        self.assignment_id = assignment_id

    def check_relevance(self) -> dict:
        from apps.assignments.models import Assignment
        from apps.syllabus.models import SyllabusTopic

        assignment = Assignment.objects.select_related(
            'subject_assignment__syllabus'
        ).get(id=self.assignment_id)

        topics = SyllabusTopic.objects.filter(
            syllabus__subject_assignment=assignment.subject_assignment
        ).values_list('title', flat=True)

        if not topics:
            return {
                'score': 0,
                'feedback': 'Sillabus yuklanmagan — moslikni tekshirib bo\'lmadi',
                'topics_covered': 0,
                'topics_out': 0,
            }

        questions = assignment.questions.values_list('question_text', flat=True)
        if not questions:
            return {
                'score': 0,
                'feedback': 'Savollar topilmadi',
                'topics_covered': 0,
                'topics_out': 0,
            }

        prompt = self._build_relevance_prompt(
            list(topics), list(questions), assignment.title
        )

        # AI mavjud bo'lmasa — deterministik zaxira tahlil (kalitsiz ham ishlaydi)
        client = self._get_client()
        if client is None:
            return self._local_relevance(list(topics), list(questions))

        try:
            response = client.messages.create(
                model=settings.AI_CONFIG.get('MODEL', 'claude-sonnet-4-6'),
                max_tokens=1000,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return self._parse_relevance_response(response.content[0].text)
        except Exception as e:
            logger.error(f'Relevance check error: {e}')
            return {
                'score': 0,
                'feedback': f'AI tahlilida xato: {str(e)}',
                'topics_covered': 0,
                'topics_out': 0,
            }

    def _build_relevance_prompt(self, topics: list, questions: list, title: str) -> str:
        topics_text = '\n'.join(f'- {t}' for t in topics)
        questions_text = '\n'.join(f'{i+1}. {q[:200]}' for i, q in enumerate(questions[:20]))

        return f"""Siz ta'lim sifat nazorati mutaxassisisiz.

TOPSHIRIQ: {title}

SILLABUS MAVZULARI:
{topics_text}

TOPSHIRIQDAGI SAVOLLAR (birinchi 20 ta):
{questions_text}

Savollar sillabusga qanchalik mos ekanligini tahlil qiling.

FAQAT JSON formatda javob bering:
{{
  "score": <0 dan 100 gacha foiz>,
  "topics_covered": <sillabusdan yoritilgan mavzular soni>,
  "topics_out": <sillabusdan tashqarida savollar soni>,
  "feedback": "<O'zbek tilida kafedra mudiri uchun izoh. Qaysi savollar mosmas, nega, qanday yaxshilash kerak>",
  "matched_topics": ["<mavzu1>", "<mavzu2>"],
  "unmatched_questions": [<savol raqamlari>]
}}"""

    def _parse_relevance_response(self, text: str) -> dict:
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {
                    'score': min(float(data.get('score', 0)), 100),
                    'feedback': data.get('feedback', ''),
                    'topics_covered': int(data.get('topics_covered', 0)),
                    'topics_out': int(data.get('topics_out', 0)),
                }
        except Exception as e:
            logger.error(f'Parse relevance response error: {e}')
        return {'score': 0, 'feedback': 'Tahlil qilib bo\'lmadi', 'topics_covered': 0, 'topics_out': 0}

    def _get_client(self):
        provider = settings.AI_CONFIG.get('PROVIDER', 'anthropic')
        try:
            if provider == 'anthropic':
                key = settings.AI_CONFIG.get('ANTHROPIC_API_KEY') or ''
                if not key:
                    return None
                import anthropic
                return anthropic.Anthropic(api_key=key)
            key = settings.AI_CONFIG.get('OPENAI_API_KEY') or ''
            if not key:
                return None
            import openai
            return openai.OpenAI(api_key=key)
        except Exception as e:
            logger.warning(f'AI klient qurilmadi, zaxira usulga: {e}')
            return None

    def _local_relevance(self, topics, questions):
        topic_words = set()
        for t in topics:
            topic_words |= {w.lower() for w in re.findall(r'\w+', t) if len(w) > 3}
        matched = 0
        for q in questions:
            q_words = {w.lower() for w in re.findall(r'\w+', q) if len(w) > 3}
            if q_words & topic_words:
                matched += 1
        total = len(questions) or 1
        ratio = matched / total
        out = total - matched
        if ratio >= 0.8:
            fb = "Savollar sillabus mavzulariga to'liq mos."
        elif ratio >= 0.5:
            fb = f"{out} ta savol sillabus mavzularidan uzoqroq."
        else:
            fb = "Ko'p savollar sillabusda yo'q mavzularga tegishli ko'rinadi."
        return {'score': round(ratio*100), 'feedback': fb, 'topics_covered': matched, 'topics_out': out}


class SyllabusParser:
    """Sillabus faylidan mavzularni ajratib oladi"""

    def __init__(self, syllabus):
        self.syllabus = syllabus

    def extract_topics(self) -> list:
        text = self._extract_text()
        if not text:
            return []

        # AI orqali mavzularni ajratish
        client = self._get_client()
        prompt = f"""Quyidagi sillabus matnidan fan mavzularini ajratib oling.

SILLABUS:
{text[:4000]}

FAQAT JSON array formatda javob bering:
[
  {{
    "title": "<Mavzu nomi>",
    "description": "<Qisqa tavsif>",
    "week": <hafta raqami yoki null>,
    "hours": <soat soni yoki 2>
  }}
]"""

        try:
            response = client.messages.create(
                model=settings.AI_CONFIG.get('MODEL', 'claude-sonnet-4-6'),
                max_tokens=2000,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return self._parse_topics_response(response.content[0].text)
        except Exception as e:
            logger.error(f'Syllabus parse error: {e}')
            return []

    def _extract_text(self) -> str:
        if not self.syllabus.file:
            return ''

        file_path = self.syllabus.file.path
        ext = file_path.lower().split('.')[-1]

        try:
            if ext == 'pdf':
                return self._extract_pdf(file_path)
            elif ext in ('docx', 'doc'):
                return self._extract_docx(file_path)
            elif ext == 'txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            logger.error(f'Text extraction error: {e}')
        return ''

    def _extract_pdf(self, path: str) -> str:
        import PyPDF2
        text = []
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text() or '')
        return '\n'.join(text)

    def _extract_docx(self, path: str) -> str:
        from docx import Document
        doc = Document(path)
        return '\n'.join(p.text for p in doc.paragraphs)

    def _parse_topics_response(self, text: str) -> list:
        try:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.error(f'Parse topics error: {e}')
        return []

    def _get_client(self):
        provider = settings.AI_CONFIG.get('PROVIDER', 'anthropic')
        if provider == 'anthropic':
            import anthropic
            return anthropic.Anthropic(api_key=settings.AI_CONFIG['ANTHROPIC_API_KEY'])
        import openai
        return openai.OpenAI(api_key=settings.AI_CONFIG['OPENAI_API_KEY'])
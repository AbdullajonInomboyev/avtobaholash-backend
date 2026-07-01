"""
To'liq demo ma'lumotlar
python manage.py create_demo_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = "To'liq demo ma'lumotlarini yaratadi"

    def handle(self, *args, **kwargs):
        self.stdout.write('Demo ma\'lumotlari yaratilmoqda...\n')

        # ── Tenant ────────────────────────────────────────────────────────────
        from apps.tenants.models import Tenant
        tenant, _ = Tenant.objects.get_or_create(
            subdomain='demo',
            defaults={
                'name': "Namangan Davlat Universiteti",
                'short_name': 'NDU',
                'email': 'info@ndu.uz',
                'phone': '+998 69 234-56-78',
                'address': "Namangan shahri, Bo'stonlik ko'chasi, 1-uy",
                'max_users': 5000,
            }
        )
        self.stdout.write(f'  ✓ Tenant: {tenant.name}')

        # ── Super Admin ────────────────────────────────────────────────────────
        admin, created = User.objects.get_or_create(
            email='admin@avtobaholash.uz',
            defaults={
                'first_name': 'Bosh', 'last_name': 'Administrator',
                'role': 'super_admin', 'is_staff': True, 'is_superuser': True,
            }
        )
        if created:
            admin.set_password('Admin@2026')
            admin.save()

        # ── Fakultetlar ────────────────────────────────────────────────────────
        from apps.organization.models import Faculty, Department, Group, StudentGroup

        dean1, c = User.objects.get_or_create(
            email='dekan1@avtobaholash.uz',
            defaults={'first_name': 'Sardor', 'last_name': 'Rahimov', 'role': 'admin', 'tenant': tenant}
        )
        if c: dean1.set_password('Admin@2026'); dean1.save()

        dean2, c = User.objects.get_or_create(
            email='dekan2@avtobaholash.uz',
            defaults={'first_name': 'Nodira', 'last_name': 'Yusupova', 'role': 'admin', 'tenant': tenant}
        )
        if c: dean2.set_password('Admin@2026'); dean2.save()

        faculty1, _ = Faculty.objects.get_or_create(
            tenant=tenant, code='IT',
            defaults={'name': 'Axborot texnologiyalari fakulteti', 'dean': dean1}
        )
        faculty2, _ = Faculty.objects.get_or_create(
            tenant=tenant, code='EK',
            defaults={'name': "Iqtisodiyot va boshqaruv fakulteti", 'dean': dean2}
        )

        # ── Kafedra mudirlari ──────────────────────────────────────────────────
        head1, c = User.objects.get_or_create(
            email='mudiri@avtobaholash.uz',
            defaults={'first_name': 'Kamoliddin', 'last_name': 'Yusupov', 'middle_name': 'Baxtiyorovich', 'role': 'department_head', 'tenant': tenant}
        )
        if c: head1.set_password('Mudiri@2026'); head1.save()

        head2, c = User.objects.get_or_create(
            email='mudiri2@avtobaholash.uz',
            defaults={'first_name': 'Dilnoza', 'last_name': 'Hasanova', 'middle_name': 'Ibrohimovna', 'role': 'department_head', 'tenant': tenant}
        )
        if c: head2.set_password('Mudiri@2026'); head2.save()

        head3, c = User.objects.get_or_create(
            email='mudiri3@avtobaholash.uz',
            defaults={'first_name': 'Jasur', 'last_name': 'Mirzayev', 'middle_name': 'Toxirovich', 'role': 'department_head', 'tenant': tenant}
        )
        if c: head3.set_password('Mudiri@2026'); head3.save()

        # ── Kafedralar ─────────────────────────────────────────────────────────
        dept1, _ = Department.objects.get_or_create(
            tenant=tenant, code='CS',
            defaults={'name': 'Kompyuter fanlari kafedrasi', 'faculty': faculty1, 'head': head1}
        )
        dept2, _ = Department.objects.get_or_create(
            tenant=tenant, code='SE',
            defaults={'name': 'Dasturiy injiniring kafedrasi', 'faculty': faculty1, 'head': head2}
        )
        dept3, _ = Department.objects.get_or_create(
            tenant=tenant, code='MG',
            defaults={'name': 'Menejment kafedrasi', 'faculty': faculty2, 'head': head3}
        )
        self.stdout.write(f'  ✓ Kafedralar yaratildi')

        # ── O'qituvchilar ──────────────────────────────────────────────────────
        teachers_data = [
            ('teacher@avtobaholash.uz', 'Malika', 'Karimova', 'Rustamovna', dept1),
            ('teacher2@avtobaholash.uz', 'Sherzod', 'Toshmatov', 'Hamidovich', dept1),
            ('teacher3@avtobaholash.uz', 'Gulnora', 'Nazarova', 'Aliyevna', dept2),
            ('teacher4@avtobaholash.uz', 'Bekzod', 'Holmatov', 'Ergashevich', dept3),
        ]
        teachers = []
        for email, fn, ln, mn, dept in teachers_data:
            t, c = User.objects.get_or_create(
                email=email,
                defaults={'first_name': fn, 'last_name': ln, 'middle_name': mn, 'role': 'teacher', 'tenant': tenant}
            )
            if c: t.set_password('Teacher@2026'); t.save()
            teachers.append((t, dept))
        self.stdout.write(f'  ✓ O\'qituvchilar: {len(teachers)} ta')

        # ── Guruhlar ───────────────────────────────────────────────────────────
        groups_data = [
            ('CS-22-01', 2022, dept1),
            ('CS-22-02', 2022, dept1),
            ('SE-23-01', 2023, dept2),
            ('MG-22-01', 2022, dept3),
        ]
        groups = []
        for name, year, dept in groups_data:
            g, _ = Group.objects.get_or_create(
                tenant=tenant, name=name, year=year,
                defaults={'department': dept}
            )
            groups.append(g)

        # ── Talabalar ──────────────────────────────────────────────────────────
        students_data = [
            ('student@avtobaholash.uz', 'Jasur', 'Toshmatov', 'CS-22-001', groups[0]),
            ('student2@avtobaholash.uz', 'Zulfiya', 'Rahimova', 'CS-22-002', groups[0]),
            ('student3@avtobaholash.uz', 'Otabek', 'Yusupov', 'CS-22-003', groups[0]),
            ('student4@avtobaholash.uz', 'Mohira', 'Azimova', 'CS-22-004', groups[0]),
            ('student5@avtobaholash.uz', 'Sardor', 'Aliyev', 'CS-22-011', groups[1]),
            ('student6@avtobaholash.uz', 'Nilufar', 'Hasanova', 'CS-22-012', groups[1]),
            ('student7@avtobaholash.uz', 'Azizbek', 'Mirzayev', 'SE-23-001', groups[2]),
            ('student8@avtobaholash.uz', 'Barno', 'Qodirov', 'MG-22-001', groups[3]),
        ]
        students = []
        for email, fn, ln, sid, group in students_data:
            s, c = User.objects.get_or_create(
                email=email,
                defaults={'first_name': fn, 'last_name': ln, 'role': 'student', 'tenant': tenant, 'student_id': sid}
            )
            if c: s.set_password('Student@2026'); s.save()
            StudentGroup.objects.get_or_create(tenant=tenant, student=s, group=group)
            students.append((s, group))
        self.stdout.write(f'  ✓ Talabalar: {len(students)} ta')

        # ── Fanlar va semestr ──────────────────────────────────────────────────
        from apps.academics.models import Subject, AcademicTerm, SubjectAssignment

        term, _ = AcademicTerm.objects.get_or_create(
            tenant=tenant, name='2025-2026 / 2-semestr',
            defaults={'start_date': '2026-02-01', 'end_date': '2026-06-30', 'is_current': True}
        )

        subjects_data = [
            ('Algoritmlar va ma\'lumotlar tuzilmasi', 'ALG101', dept1, 6),
            ('Dasturlash asoslari (Python)', 'PY101', dept1, 5),
            ('Ma\'lumotlar bazasi', 'DB201', dept2, 4),
            ('Menejment asoslari', 'MG101', dept3, 4),
        ]
        subjects = []
        for name, code, dept, credits in subjects_data:
            s, _ = Subject.objects.get_or_create(
                tenant=tenant, code=code,
                defaults={'name': name, 'department': dept, 'credit_hours': credits}
            )
            subjects.append(s)
        self.stdout.write(f'  ✓ Fanlar: {len(subjects)} ta')

        # ── Fan biriktirilishi ─────────────────────────────────────────────────
        sa_map = [
            (subjects[0], teachers[0][0], groups[0], dept1),
            (subjects[0], teachers[1][0], groups[1], dept1),
            (subjects[1], teachers[0][0], groups[0], dept1),
            (subjects[2], teachers[2][0], groups[2], dept2),
            (subjects[3], teachers[3][0], groups[3], dept3),
        ]
        subject_assignments = []
        for subj, teacher, group, dept in sa_map:
            sa, _ = SubjectAssignment.objects.get_or_create(
                tenant=tenant, subject=subj, teacher=teacher, group=group, term=term
            )
            subject_assignments.append(sa)
        self.stdout.write(f'  ✓ Fan biriktirilishi: {len(subject_assignments)} ta')

        # ── Sillabus ──────────────────────────────────────────────────────────
        from apps.syllabus.models import Syllabus, SyllabusTopic

        syllabus_topics = {
            subject_assignments[0]: [
                ('Algoritmlar va murakkablik', 'Algoritmlar tahlili va Big-O notation', 1, 4),
                ('Massivlar va bog\'langan ro\'yxatlar', 'Massiv va linked list operatsiyalari', 2, 4),
                ('Stek va navbat', 'Stack va Queue ma\'lumotlar tuzilmasi', 3, 4),
                ('Daraxt tuzilmalari', 'Binary tree va BST', 4, 4),
                ('Saralash algoritmlari', 'Bubble, Quick, Merge sort', 5, 4),
                ('Qidiruv algoritmlari', 'Linear va binary search', 6, 4),
            ],
            subject_assignments[2]: [
                ('Python asoslari', 'O\'zgaruvchilar, operatorlar va shartlar', 1, 4),
                ('Funksiyalar', 'Funksiya yaratish va parametrlar', 2, 4),
                ('OOP asoslari', 'Klass va obyektlar', 3, 4),
                ('Fayllar bilan ishlash', 'Fayl o\'qish va yozish', 4, 4),
            ],
        }

        for sa, topics in syllabus_topics.items():
            syllabus, _ = Syllabus.objects.get_or_create(
                tenant=tenant, subject_assignment=sa,
                defaults={'ai_processed': True, 'parsed_text': 'Demo sillabus'}
            )
            for i, (title, desc, week, hours) in enumerate(topics, 1):
                SyllabusTopic.objects.get_or_create(
                    tenant=tenant, syllabus=syllabus, topic_number=i,
                    defaults={'title': title, 'description': desc, 'week_number': week, 'hours': hours}
                )
        self.stdout.write(f'  ✓ Sillabus va mavzular yaratildi')

        # ── Topshiriqlar ──────────────────────────────────────────────────────
        from apps.assignments.models import Assignment, Question, AnswerOption, AssignmentType

        now = timezone.now()

        assignments_data = [
            # (sa_index, title, type, start_offset_days, end_offset_days, duration)
            (0, '1-oraliq nazorat: Algoritmlar', 'test', -10, 5, 60),
            (0, 'Mustaqil ish: Saralash algoritmlari', 'written', -5, 3, 90),
            (2, 'Python: OOP topshirig\'i', 'test', -7, 2, 45),
            (3, 'Ma\'lumotlar bazasi: SQL vazifasi', 'test', -3, 7, 60),
        ]

        created_assignments = []
        for sa_idx, title, atype, start_offset, end_offset, duration in assignments_data:
            sa = subject_assignments[sa_idx]
            a, _ = Assignment.objects.get_or_create(
                tenant=tenant,
                subject_assignment=sa,
                title=title,
                defaults={
                    'teacher': sa.teacher,
                    'assignment_type': atype,
                    'duration_minutes': duration,
                    'start_datetime': now + timedelta(days=start_offset),
                    'end_datetime': now + timedelta(days=end_offset),
                    'is_published': True,
                    'shuffle_questions': True,
                    'ai_relevance_score': 87.5,
                    'ai_relevance_feedback': 'Topshiriq sillabusga 87.5% mos keladi.',
                }
            )
            created_assignments.append(a)
        self.stdout.write(f'  ✓ Topshiriqlar: {len(created_assignments)} ta')

        # ── Savollar ──────────────────────────────────────────────────────────
        questions_data = [
            # (assignment_index, question_text, options [(text, is_correct)])
            (0, 'Big-O notatsiyada O(n²) qaysi algoritmga tegishli?', [
                ('Bubble sort', True), ('Binary search', False),
                ('Merge sort', False), ('Linear search', False)
            ]),
            (0, 'Quyidagilardan qaysi biri ma\'lumotlar tuzilmasi emas?', [
                ('Stack', False), ('Queue', False),
                ('Compiler', True), ('Array', False)
            ]),
            (0, 'Binary search qaysi shartda ishlaydi?', [
                ('Massiv tartiblangan bo\'lishi kerak', True),
                ('Massiv tartiblangan bo\'lmasligi kerak', False),
                ('Massiv bo\'sh bo\'lishi kerak', False),
                ('Massiv faqat raqamlardan iborat bo\'lishi kerak', False)
            ]),
            (0, 'Linked list va array orasidagi asosiy farq nima?', [
                ('Linked list dinamik o\'lchamga ega', True),
                ('Array tezroq ishlaydi', False),
                ('Linked list ko\'proq xotira ishlatadi', False),
                ('Farq yo\'q', False)
            ]),
            (0, 'Stack ma\'lumotlar tuzilmasida asosiy operatsiya?', [
                ('LIFO - oxirgi kirgani birinchi chiqadi', True),
                ('FIFO - birinchi kirgani birinchi chiqadi', False),
                ('Random - tasodifiy chiqadi', False),
                ('FILO - birinchi kirgani oxirgi chiqadi', False)
            ]),
            (2, 'Python da list yaratish uchun qaysi sintaksis to\'g\'ri?', [
                ('my_list = []', True), ('my_list = {}', False),
                ('my_list = ()', False), ('my_list = <>',  False)
            ]),
            (2, 'Python da class yaratish kalit so\'zi?', [
                ('class', True), ('def', False), ('object', False), ('new', False)
            ]),
            (2, 'Python da inheritance (meros olish) qanday yoziladi?', [
                ('class Child(Parent):', True),
                ('class Child extends Parent:', False),
                ('class Child implements Parent:', False),
                ('class Child :: Parent:', False)
            ]),
            (3, 'SQL da jadvaldan ma\'lumot olish operatori?', [
                ('SELECT', True), ('GET', False), ('FETCH', False), ('READ', False)
            ]),
            (3, 'SQL da yangi qator qo\'shish operatori?', [
                ('INSERT INTO', True), ('ADD INTO', False),
                ('PUT INTO', False), ('CREATE INTO', False)
            ]),
        ]

        created_questions = []
        for a_idx, q_text, options in questions_data:
            assignment = created_assignments[a_idx]
            q, _ = Question.objects.get_or_create(
                tenant=tenant, assignment=assignment, question_text=q_text,
                defaults={
                    'question_type': 'single_choice',
                    'points': 1.0,
                    'order_index': len(created_questions),
                    'is_tts_readable': True,
                    'tts_text': q_text,
                }
            )
            for i, (opt_text, is_correct) in enumerate(options):
                AnswerOption.objects.get_or_create(
                    tenant=tenant, question=q, option_text=opt_text,
                    defaults={'is_correct': is_correct, 'order_index': i}
                )
            created_questions.append(q)
        self.stdout.write(f'  ✓ Savollar: {len(created_questions)} ta')

        # ── Talabalar topshiriq bajardi ────────────────────────────────────────
        from apps.submissions.models import AssignmentSubmission, SubmissionAnswer, SubmissionStatus
        from apps.grading.models import AIGradingResult, Gradebook
        import random

        # Faqat birinchi guruh talabalari (CS-22-01) birinchi topshiriqni bajardi
        group1_students = [s for s, g in students if g == groups[0]]
        first_assignment = created_assignments[0]

        grades_dist = [5, 5, 4, 4, 3]  # 5 ta talaba uchun baholar

        for i, student in enumerate(group1_students[:5]):
            sub, _ = AssignmentSubmission.objects.get_or_create(
                tenant=tenant, assignment=first_assignment, student=student,
                defaults={
                    'status': SubmissionStatus.GRADED,
                    'started_at': now - timedelta(days=8),
                    'submitted_at': now - timedelta(days=8, hours=-1),
                    'time_spent_seconds': random.randint(1800, 3300),
                }
            )

            # To'g'ri javoblarni topamiz
            assignment_questions = Question.objects.filter(
                assignment=first_assignment
            ).prefetch_related('options')

            total_score = 0
            max_total = 0

            for q in assignment_questions:
                correct_option = q.options.filter(is_correct=True).first()
                # Ba'zi talabalar noto'g'ri javob beradi
                if i < grades_dist.count(5) or random.random() > 0.3:
                    selected = correct_option
                    score = float(q.points)
                else:
                    selected = q.options.exclude(is_correct=True).first()
                    score = 0

                if selected:
                    ans, _ = SubmissionAnswer.objects.get_or_create(
                        tenant=tenant, submission=sub, question=q
                    )
                    ans.selected_options.set([selected])

                total_score += score
                max_total += float(q.points)

                AIGradingResult.objects.get_or_create(
                    tenant=tenant, submission=sub, question=q,
                    defaults={
                        'score': score, 'max_score': float(q.points),
                        'feedback': "To'g'ri" if score > 0 else "Noto'g'ri javob",
                        'confidence': 0.95,
                        'model_used': 'demo',
                    }
                )

            grade = grades_dist[i] if i < len(grades_dist) else 3

            # Umumiy AI baho
            AIGradingResult.objects.get_or_create(
                tenant=tenant, submission=sub, question=None,
                defaults={
                    'score': total_score, 'max_score': max_total,
                    'feedback': f'Umumiy ball: {total_score}/{max_total}. Siz {grade} baho oldingiz.',
                    'confidence': 0.95, 'model_used': 'demo',
                }
            )

            # Jurnal
            Gradebook.objects.get_or_create(
                tenant=tenant,
                subject_assignment=first_assignment.subject_assignment,
                student=student,
                assignment=first_assignment,
                defaults={
                    'final_score': total_score,
                    'grade': grade,
                    'is_confirmed': True,
                    'confirmed_at': now - timedelta(days=7),
                    'confirmed_by': first_assignment.teacher,
                }
            )

        self.stdout.write(f'  ✓ Topshiriq javoblari va baholar yaratildi')

        # ── O'qituvchi baholash jurnali (kafedra uchun) ────────────────────────
        from apps.grading.models import TeacherEvaluationLog

        for sa in subject_assignments[:3]:
            TeacherEvaluationLog.objects.get_or_create(
                tenant=tenant, teacher=sa.teacher, assignment=created_assignments[0],
                defaults={
                    'syllabus_match_score': random.uniform(75, 95),
                    'topics_covered': random.randint(4, 6),
                    'topics_out_of_syllabus': random.randint(0, 1),
                    'question_quality_score': random.uniform(80, 95),
                    'ai_feedback': 'Topshiriq sillabusga yaxshi mos keladi.',
                }
            )
        self.stdout.write(f'  ✓ O\'qituvchi baholash jurnali yaratildi')

        # ── Bildirishnomalar ───────────────────────────────────────────────────
        from apps.notifications.models import Notification

        notif_data = [
            (students[0][0], 'Bahongiz qo\'yildi!', '1-oraliq nazorat bo\'yicha bahongiz: 5', 'grade'),
            (students[1][0], 'Yangi topshiriq', 'Algoritmlar fanidan yangi topshiriq berildi', 'assignment'),
            (teachers[0][0], '5 talaba topshirdi', 'CS-22-01 guruhidan 5 talaba topshiriqni topshirdi', 'assignment'),
            (head1, 'Sillabus og\'ishi', 'Sherzod Toshmatov sillabusdan chetga chiqdi (61%)', 'system'),
        ]
        for recipient, title, body, ntype in notif_data:
            Notification.objects.get_or_create(
                tenant=tenant, recipient=recipient, title=title,
                defaults={'body': body, 'notification_type': ntype}
            )
        self.stdout.write(f'  ✓ Bildirishnomalar yaratildi')

        # ── Xulosa ────────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS('\n✅ To\'liq demo ma\'lumotlari yaratildi!\n'))
        self.stdout.write('Login ma\'lumotlari:')
        self.stdout.write('  Admin:          admin@avtobaholash.uz    / Admin@2026')
        self.stdout.write('  Kafedra mudiri: mudiri@avtobaholash.uz   / Mudiri@2026')
        self.stdout.write("  O'qituvchi:     teacher@avtobaholash.uz  / Teacher@2026")
        self.stdout.write('  Talaba:         student@avtobaholash.uz  / Student@2026')
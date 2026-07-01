"""
Excel Export — Jurnal xlsx formatda
"""
import io
import xlsxwriter
from django.utils import timezone


class GradebookExcelExporter:
    def __init__(self, subject_assignment, entries):
        self.sa = subject_assignment
        self.entries = list(entries)

    def generate(self) -> io.BytesIO:
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        ws = workbook.add_worksheet('Jurnal')

        # Formatlar
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#1e3a7b', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
        })
        cell_fmt = workbook.add_format({'border': 1, 'align': 'center'})
        name_fmt = workbook.add_format({'border': 1})
        grade5_fmt = workbook.add_format({'border': 1, 'bg_color': '#c6efce', 'align': 'center'})
        grade4_fmt = workbook.add_format({'border': 1, 'bg_color': '#ffeb9c', 'align': 'center'})
        grade3_fmt = workbook.add_format({'border': 1, 'bg_color': '#ffcc99', 'align': 'center'})
        grade2_fmt = workbook.add_format({'border': 1, 'bg_color': '#ffc7ce', 'align': 'center'})

        # Sarlavha
        ws.merge_range('A1:F1', f'JURNAL: {self.sa.subject.name}', header_fmt)
        ws.merge_range('A2:F2',
                       f'Guruh: {self.sa.group.name} | '
                       f'O\'qituvchi: {self.sa.teacher.full_name} | '
                       f'Sana: {timezone.now().strftime("%d.%m.%Y")}',
                       workbook.add_format({'bold': True, 'align': 'center'}))

        # Ustun boshlari
        headers = ['#', 'Talaba ID', 'F.I.Sh.', 'Ball', 'Baho', 'Holat']
        col_widths = [5, 15, 35, 10, 10, 15]

        for col, (h, w) in enumerate(zip(headers, col_widths)):
            ws.write(3, col, h, header_fmt)
            ws.set_column(col, col, w)

        ws.set_row(3, 20)

        # Ma'lumotlar
        grade_fmts = {5: grade5_fmt, 4: grade4_fmt, 3: grade3_fmt, 2: grade2_fmt}

        for row_idx, entry in enumerate(self.entries, start=4):
            grade_fmt = grade_fmts.get(entry.grade, cell_fmt)
            ws.write(row_idx, 0, row_idx - 3, cell_fmt)
            ws.write(row_idx, 1, entry.student.student_id or '-', cell_fmt)
            ws.write(row_idx, 2, entry.student.full_name, name_fmt)
            ws.write(row_idx, 3, float(entry.final_score), cell_fmt)
            ws.write(row_idx, 4, entry.grade, grade_fmt)
            ws.write(row_idx, 5, 'Tasdiqlangan' if entry.is_confirmed else 'Kutilmoqda', cell_fmt)

        # Statistika
        last_row = len(self.entries) + 5
        ws.write(last_row, 2, "O'rtacha baho:", workbook.add_format({'bold': True}))
        ws.write_formula(last_row, 4, f'=AVERAGE(E5:E{last_row - 1})',
                        workbook.add_format({'bold': True, 'num_format': '0.00'}))

        workbook.close()
        buffer.seek(0)
        return buffer

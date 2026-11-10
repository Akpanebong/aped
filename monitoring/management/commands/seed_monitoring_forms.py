from pathlib import Path
import re
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from openpyxl import load_workbook
from monitoring.models import MonitoringForm

WORKBOOK_NAME = "APED Monitoring Forms.xlsx"
CATEGORY_BY_SHEET = {"APED Farmer Monitoring Form": "agriculture", "APED Pig Monitoring Form": "livestock", "APED Goat Monitoring Form": "livestock", "APED Beekeeping Monitoring Form": "apiary", "Peacebuilding Forms Package": "peacebuilding"}
DESCRIPTION_BY_CATEGORY = {"agriculture": "Seed distribution, planting, crop establishment, management, support and recommendations.", "livestock": "Animal distribution, housing, feeding, health, growth, benefits and follow-up.", "apiary": "Hive distribution, colony development, apiary practices, production and support.", "peacebuilding": "Dialogue, conflict incidents, training, mediation and peacebuilding impact."}


class Command(BaseCommand):
    help = "Create or update APED monitoring forms from the workbook, excluding standalone VSLA forms."

    def add_arguments(self, parser):
        parser.add_argument("workbook", nargs="?", type=Path, default=settings.BASE_DIR / WORKBOOK_NAME)

    def handle(self, *args, **options):
        workbook_path = options["workbook"]
        if not workbook_path.exists():
            raise CommandError(f"Workbook not found: {workbook_path}. Pass its path as an argument.")
        workbook = load_workbook(workbook_path, data_only=True)
        for sheet_name, category in CATEGORY_BY_SHEET.items():
            if sheet_name not in workbook.sheetnames:
                self.stderr.write(self.style.WARNING(f"Sheet not found: {sheet_name}"))
                continue
            worksheet = workbook[sheet_name]
            name = str(worksheet.cell(1, 1).value or sheet_name).strip()
            obj, created = MonitoringForm.objects.update_or_create(slug=slugify(name), defaults={"name": name, "category": category, "description": DESCRIPTION_BY_CATEGORY[category], "schema": self.parse_sheet(worksheet), "is_active": True})
            self.stdout.write(f"{'Created' if created else 'Updated'} {name}")

    def parse_sheet(self, worksheet):
        rows = [[str(value).strip() if value is not None else "" for value in row] for row in worksheet.iter_rows(values_only=True)]
        if worksheet.title == "Field Visit Attendance Sheet":
            return [self.make_section("Activity Details", ["Activity", "Village", "Date", "Facilitator", "Project"], False, 1), self.make_section("Participant Attendance", ["Participant Name", "Gender", "Age", "Age Group (18-35/35+)", "Disability Status?", "Disability Type", "Contact", "Signature/Attendance Confirmation", "Notes"], True, 2)]
        starts = [index for index, row in enumerate(rows) if row and row[0].lower().startswith("section")]
        schema = []
        for position, start in enumerate(starts):
            end = starts[position + 1] if position + 1 < len(starts) else len(rows)
            content = [row for row in rows[start + 1:end] if any(row)]
            if not content:
                continue
            header = content[0]
            if header[0].lower() in {"field", "aspect", "topic"}:
                labels, repeatable = [row[0] for row in content[1:] if row[0]], False
            else:
                first = header[0] if header[0] and header[0] != "#" else ""
                labels, repeatable = ([first] if first else []) + [value for value in header[1:] if value], True
            if labels:
                schema.append(self.make_section(rows[start][0], labels, repeatable, len(schema) + 1))
        return schema

    def make_section(self, title, labels, repeatable, number):
        return {"title": title, "key": f"section_{number}", "repeatable": repeatable, "fields": [{"name": f"field_{index}", "label": label, "type": self.field_type(label), "choices": self.field_choices(label)} for index, label in enumerate(labels, 1)]}

    def field_type(self, label):
        value = label.lower()
        if "signature" in value or "phone" in value or re.search(r"\bid\b", value): return "text"
        if any(token in value for token in ["number", "amount", "quantity", "weight", "rate", "distance", "participants", "members", "shares", "interest", "sessions", "kids", "people affected"]): return "number"
        if "date" in value or "dates" in value: return "date"
        if "?" in value or any(token in value for token in ["yes/no", "y/n", "gender", "condition", "rating", "status"]): return "select"
        if any(token in value for token in ["comments", "description", "notes", "summary", "symptoms", "observations", "recommendations", "challenges", "feedback", "purpose", "actions", "remarks", "outcome"]): return "textarea"
        return "text"

    def field_choices(self, label):
        value = label.lower()
        if "gender" in value: return ["Male", "Female", "Other", "Prefer not to say"]
        if "age group" in value: return ["18-35", "35+"]
        if "yes/no" in value or "y/n" in value or "?" in value: return ["Yes", "No", "Not applicable"]
        if "rating" in value: return ["1", "2", "3", "4", "5"]
        return []

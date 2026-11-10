"""Selectable model sources used by linked monitoring-form questions."""

from core.models import Activity, FieldAttendance, FieldAttendancePart, Project
from monitoring.models import FollowUpAction, MonitoringRecord
from vsla_app.vsla.models import Loan, LoanRepayment, MeetingAttendance, SocialFundTransaction, SavingsTransaction, VSLAChallengeStory, VSLAGroup, VSLA_Meeting, VSLAMember

LINKED_RECORD_SOURCES = {
    'project': ('Projects', Project, ('name',)),
    'activity': ('Programme activities', Activity, ('activity_name',)),
    'field_attendance': ('Attendance sheets', FieldAttendance, ('-activity_date', '-created_at')),
    'field_attendance_participant': ('Attendance participants', FieldAttendancePart, ('name',)),
    'monitoring_record': ('Monitoring records', MonitoringRecord, ('-visit_date', '-created_at')),
    'follow_up_action': ('Follow-up actions', FollowUpAction, ('due_date', '-created_at')),
    'vsla_group': ('VSLA groups', VSLAGroup, ('name',)),
    'vsla_member': ('VSLA members', VSLAMember, ('last_name', 'first_name')),
    'vsla_meeting': ('VSLA meetings', VSLA_Meeting, ('-meeting_date',)),
    'vsla_meeting_attendance': ('VSLA meeting attendance', MeetingAttendance, ('-created_at',)),
    'vsla_savings_transaction': ('VSLA savings transactions', SavingsTransaction, ('-transaction_date',)),
    'vsla_loan': ('VSLA loans', Loan, ('-application_date',)),
    'vsla_loan_repayment': ('VSLA loan repayments', LoanRepayment, ('-transaction_date',)),
    'vsla_social_fund_transaction': ('VSLA social fund transactions', SocialFundTransaction, ('-transaction_date',)),
    'vsla_challenge_story': ('VSLA challenge and success stories', VSLAChallengeStory, ('-entry_date',)),
}


def linked_record_choices(source):
    definition = LINKED_RECORD_SOURCES.get(source)
    if not definition:
        return []
    queryset = definition[1].objects.all().order_by(*definition[2])
    return [(str(item.pk), str(item)) for item in queryset]

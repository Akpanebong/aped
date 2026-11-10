from django.urls import path
from . import views

app_name = "vsla"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("groups/", views.group_list, name="groups"),
    path("groups/new/", views.group_create, name="group_create"),
    path("groups/<slug:slug>/", views.group_detail, name="group_detail"),
    path("members/", views.member_list, name="members"),
    path("members/new/", views.member_create, name="member_create"),
    path("members/<slug:member_no>/", views.member_detail, name="member_detail"),
    path("savings/", views.savings_list, name="savings"),
    path("savings/new/", views.savings_create, name="savings_create"),
    path("loans/", views.loan_list, name="loans"),
    path("loans/new/", views.loan_create, name="loan_create"),
    path("loans/<slug:loan_no>/", views.loan_detail, name="loan_detail"),
    path("loans/<slug:loan_no>/submit/", views.loan_submit, name="loan_submit"),
    path("loans/<slug:loan_no>/decision/", views.loan_decision, name="loan_decision"),
    path("loans/<slug:loan_no>/repay/", views.repayment_create, name="repayment_create"),
    path("meetings/", views.meeting_list, name="meetings"),
    path("meetings/new/", views.meeting_create, name="meeting_create"),
    path("social-fund/", views.social_fund_list, name="social_fund"),
    path("social-fund/new/", views.social_fund_create, name="social_fund_create"),
    path("share-out/", views.share_out_summary, name="share_out"),
    path("challenges-stories/", views.challenge_story_list, name="challenge_stories"),
    path("challenges-stories/new/", views.challenge_story_create, name="challenge_story_create"),
    path("exports/workbook.xlsx", views.export_workbook, name="export_workbook"),
    path("exports/groups.csv", views.export_groups, name="export_groups"),
    path("exports/members.csv", views.export_members, name="export_members"),
    path("exports/savings.csv", views.export_savings, name="export_savings"),
    path("exports/loans.csv", views.export_loans, name="export_loans"),
    path("exports/meetings.csv", views.export_meetings, name="export_meetings"),
    path("exports/social-fund.csv", views.export_social_fund, name="export_social_fund"),
    path("exports/challenges-stories.csv", views.export_challenge_stories, name="export_challenge_stories"),
]

import csv
import json
from decimal import Decimal
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Count
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook

from .access import vsla_access_required
from .forms import VSLAGroupForm, VSLAMemberForm, SavingsTransactionForm, LoanForm, LoanRepaymentForm, VSLA_MeetingForm, SocialFundTransactionForm, VSLAChallengeStoryForm
from .models import VSLAGroup, VSLAMember, SavingsTransaction, Loan, LoanRepayment, VSLA_Meeting, MeetingAttendance, SocialFundTransaction, VSLAChallengeStory, LedgerEntry

from decimal import Decimal

from django.db.models import (
    Count,
    Sum,
    Q,
    F,
    Value,
    Case,
    When,
    OuterRef,
    Subquery,
    ExpressionWrapper,
    DecimalField,
)
from django.db.models.functions import Coalesce
from django.shortcuts import render


@vsla_access_required
def dashboard(request):
    """Optimized VSLA dashboard with database-side portfolio calculations."""

    ZERO = Decimal("0.00")
    MONEY = DecimalField(max_digits=18, decimal_places=2)

    group_id = request.GET.get("group", "")
    group_status = request.GET.get("group_status", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    dashboard_groups = VSLAGroup.objects.all()
    if group_id:
        dashboard_groups = dashboard_groups.filter(pk=group_id)
    if group_status:
        dashboard_groups = dashboard_groups.filter(status=group_status)
    dashboard_group_ids = dashboard_groups.values("pk")

    zero_value = Value(ZERO, output_field=MONEY)
    hundred_value = Value(Decimal("100"), output_field=MONEY)

    # ---------------------------------------------------------
    # 1. Groups and members
    # ---------------------------------------------------------
    group_stats = dashboard_groups.aggregate(
        total_groups=Count("pk"),
        active_groups=Count(
            "pk",
            filter=Q(status=VSLAGroup.Status.ACTIVE),
        ),
    )

    dashboard_members = VSLAMember.objects.filter(group_id__in=dashboard_group_ids)
    member_stats = dashboard_members.aggregate(
        total_members=Count("pk"),
        active_members=Count(
            "pk",
            filter=Q(status=VSLAMember.Status.ACTIVE),
        ),
    )

    # ---------------------------------------------------------
    # 2. Posted savings
    # ---------------------------------------------------------
    posted_savings = SavingsTransaction.objects.filter(
        status=LedgerEntry.Status.POSTED,
        group_id__in=dashboard_group_ids,
    )
    if start:
        posted_savings = posted_savings.filter(transaction_date__gte=start)
    if end:
        posted_savings = posted_savings.filter(transaction_date__lte=end)

    savings_stats = posted_savings.aggregate(
        total_savings=Sum(
            "amount",
            filter=Q(
                transaction_type=SavingsTransaction.Type.DEPOSIT,
            ),
        ),
        withdrawals=Sum(
            "amount",
            filter=Q(
                transaction_type__in=[
                    SavingsTransaction.Type.WITHDRAWAL,
                    SavingsTransaction.Type.SHARE_OUT,
                ],
            ),
        ),
    )

    total_savings = savings_stats["total_savings"] or ZERO
    withdrawals = savings_stats["withdrawals"] or ZERO
    net_savings = total_savings - withdrawals

    # ---------------------------------------------------------
    # 3. Loan portfolio
    # ---------------------------------------------------------
    # Calculate posted repayments per loan in a correlated
    # subquery, avoiding a query for every loan property.
    repayment_totals = (
        LoanRepayment.objects.filter(
            loan_id=OuterRef("pk"),
            status=LedgerEntry.Status.POSTED,
        )
        .order_by()
        .values("loan_id")
        .annotate(total=Sum("amount"))
        .values("total")[:1]
    )

    loan_portfolio = Loan.objects.filter(group_id__in=dashboard_group_ids)
    if start:
        loan_portfolio = loan_portfolio.filter(application_date__gte=start)
    if end:
        loan_portfolio = loan_portfolio.filter(application_date__lte=end)
    loan_portfolio = loan_portfolio.annotate(
        dashboard_principal=Coalesce(
            "approved_amount",
            "requested_amount",
            output_field=MONEY,
        ),
        dashboard_repaid=Coalesce(
            Subquery(repayment_totals, output_field=MONEY),
            zero_value,
            output_field=MONEY,
        ),
    ).annotate(
        dashboard_total_due=ExpressionWrapper(
            F("dashboard_principal")
            * (
                hundred_value + F("interest_rate")
            )
            / hundred_value,
            output_field=MONEY,
        ),
    ).annotate(
        dashboard_outstanding=Case(
            When(
                dashboard_total_due__gt=F("dashboard_repaid"),
                then=ExpressionWrapper(
                    F("dashboard_total_due") - F("dashboard_repaid"),
                    output_field=MONEY,
                ),
            ),
            default=zero_value,
            output_field=MONEY,
        ),
    )

    loan_stats = loan_portfolio.aggregate(
        loan_disbursed=Sum(
            "approved_amount",
            filter=Q(
                status__in=[
                    Loan.Status.DISBURSED,
                    Loan.Status.CLOSED,
                ],
            ),
        ),
        outstanding=Sum(
            "dashboard_outstanding",
            filter=Q(status=Loan.Status.DISBURSED),
        ),
        pending_loans=Count(
            "pk",
            filter=Q(status=Loan.Status.SUBMITTED),
        ),
    )

    loan_disbursed = loan_stats["loan_disbursed"] or ZERO
    outstanding = loan_stats["outstanding"] or ZERO

    # Actual posted repayments, rather than estimating repayment
    # as disbursed principal minus outstanding principal.
    total_repaid = (
        LoanRepayment.objects.filter(
            status=LedgerEntry.Status.POSTED,
            loan__status__in=[
                Loan.Status.DISBURSED,
                Loan.Status.CLOSED,
            ],
            loan__group_id__in=dashboard_group_ids,
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    # ---------------------------------------------------------
    # 4. Social fund
    # ---------------------------------------------------------
    social_stats = SocialFundTransaction.objects.filter(
        status=LedgerEntry.Status.POSTED,
        group_id__in=dashboard_group_ids,
    ).aggregate(
        social_in=Sum(
            "amount",
            filter=Q(
                transaction_type=SocialFundTransaction.Type.CONTRIBUTION,
            ),
        ),
        social_out=Sum(
            "amount",
            filter=Q(
                transaction_type=SocialFundTransaction.Type.SUPPORT,
            ),
        ),
    )

    social_in = social_stats["social_in"] or ZERO
    social_out = social_stats["social_out"] or ZERO
    social_fund_balance = social_in - social_out

    # ---------------------------------------------------------
    # 5. Group status chart
    # ---------------------------------------------------------
    status_counts = list(
        dashboard_groups.values("status")
        .annotate(total=Count("pk"))
        .order_by("status")
    )

    # ---------------------------------------------------------
    # 6. Recent posted savings and recent loan applications
    # ---------------------------------------------------------
    recent_savings = (
        posted_savings.select_related("group", "member")
        .order_by("-transaction_date", "-created_at")[:8]
    )

    recent_loans = (
        loan_portfolio.select_related("group", "member")
        .order_by("-created_at")[:6]
    )

    # ---------------------------------------------------------
    # 7. Chart data
    # ---------------------------------------------------------
    chart_data = {
        "groupLabels": [
            (item["status"] or "unknown")
            .replace("_", " ")
            .title()
            for item in status_counts
        ],
        "groupValues": [
            item["total"] for item in status_counts
        ],
        "savingsLabels": [
            "Deposits",
            "Withdrawals / share-outs",
        ],
        "savingsValues": [
            float(total_savings),
            float(withdrawals),
        ],
        "loanLabels": [
            "Outstanding",
            "Posted repayments",
        ],
        "loanValues": [
            float(outstanding),
            float(total_repaid),
        ],
    }

    # ---------------------------------------------------------
    # 8. Template context — preserve existing variable names
    # ---------------------------------------------------------
    context = {
        "title": "VSLA Intelligence Dashboard",

        "total_groups": group_stats["total_groups"],
        "active_groups": group_stats["active_groups"],

        "total_members": member_stats["total_members"],
        "active_members": member_stats["active_members"],

        "total_savings": total_savings,
        "net_savings": net_savings,

        "loan_disbursed": loan_disbursed,
        "outstanding_loans": outstanding,
        "pending_loans": loan_stats["pending_loans"],

        "social_fund_balance": social_fund_balance,

        "recent_savings": recent_savings,
        "recent_loans": recent_loans,

        "groups": VSLAGroup.objects.order_by("name"),
        "group_statuses": VSLAGroup.Status.choices,
        "selected_group": group_id,
        "selected_group_status": group_status,
        "start": start,
        "end": end,

        "chart_data": chart_data,
    }

    return render(request, "vsla/dashboard.html", context)


@vsla_access_required
def group_list(request):
    qs = VSLAGroup.objects.annotate(member_total=Count("members")).order_by("name")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    district = request.GET.get("district", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(district__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if district:
        qs = qs.filter(district__icontains=district)
    return render(request, "vsla/group_list.html", {"groups": qs, "q": q, "selected_status": status, "district": district, "statuses": VSLAGroup.Status.choices, "title": "VSLA Groups"})


@vsla_access_required
def group_create(request):
    form = VSLAGroupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, "VSLA group registered successfully.")
        return redirect("vsla:group_detail", slug=obj.slug)
    return render(request, "vsla/form.html", {"form": form, "title": "Register VSLA Group", "eyebrow": "GROUP MANAGEMENT", "cancel_url": "vsla:groups"})


@vsla_access_required
def group_detail(request, slug):
    group = get_object_or_404(VSLAGroup, slug=slug)
    members = group.members.all()
    transactions = group.savings_transactions.select_related("member", "recorded_by").order_by("-transaction_date")[:12]
    loans = group.loans.select_related("member").order_by("-created_at")[:10]
    deposits = group.savings_transactions.filter(status=LedgerEntry.Status.POSTED, transaction_type=SavingsTransaction.Type.DEPOSIT).aggregate(v=Sum("amount"))["v"] or Decimal("0")
    withdrawals = group.savings_transactions.filter(status=LedgerEntry.Status.POSTED, transaction_type__in=[SavingsTransaction.Type.WITHDRAWAL, SavingsTransaction.Type.SHARE_OUT]).aggregate(v=Sum("amount"))["v"] or Decimal("0")
    return render(request, "vsla/group_detail.html", {"group": group, "members": members, "transactions": transactions, "loans": loans, "group_savings": deposits-withdrawals, "title": group.name})


@vsla_access_required
def member_list(request):
    qs = VSLAMember.objects.select_related("group").all()
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(first_name__icontains=q) | qs.filter(last_name__icontains=q) | qs.filter(member_no__icontains=q) | qs.filter(phone__icontains=q)
    group_id = request.GET.get("group")
    status = request.GET.get("status", "")
    gender = request.GET.get("gender", "")
    if group_id:
        qs = qs.filter(group_id=group_id)
    if status:
        qs = qs.filter(status=status)
    if gender:
        qs = qs.filter(gender=gender)
    return render(request, "vsla/member_list.html", {"members": qs, "groups": VSLAGroup.objects.order_by("name"), "q": q, "selected_group": group_id, "selected_status": status, "selected_gender": gender, "statuses": VSLAMember.Status.choices, "genders": VSLAMember.Gender.choices, "title": "VSLA Members"})


@vsla_access_required
def member_create(request):
    initial = {}
    group_id = request.GET.get("group")
    if group_id and VSLAGroup.objects.filter(pk=group_id).exists():
        initial["group"] = group_id
    form = VSLAMemberForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.registered_by = request.user
        obj.save()
        messages.success(request, f"{obj.full_name} was registered successfully.")
        return redirect("vsla:member_detail", member_no=obj.member_no)
    return render(request, "vsla/form.html", {"form": form, "title": "Register Member", "eyebrow": "MEMBER REGISTRY", "cancel_url": "vsla:members"})


@vsla_access_required
def member_detail(request, member_no):
    member = get_object_or_404(VSLAMember.objects.select_related("group"), member_no=member_no)
    savings = member.savings_transactions.order_by("-transaction_date", "-created_at")[:20]
    loans = member.loans.order_by("-created_at")
    total_saved = member.savings_transactions.filter(status=LedgerEntry.Status.POSTED, transaction_type=SavingsTransaction.Type.DEPOSIT).aggregate(v=Sum("amount"))["v"] or Decimal("0")
    total_out = member.savings_transactions.filter(status=LedgerEntry.Status.POSTED, transaction_type__in=[SavingsTransaction.Type.WITHDRAWAL, SavingsTransaction.Type.SHARE_OUT]).aggregate(v=Sum("amount"))["v"] or Decimal("0")
    return render(request, "vsla/member_detail.html", {"member": member, "savings": savings, "loans": loans, "member_balance": total_saved-total_out, "title": member.full_name})


@vsla_access_required
def savings_list(request):
    qs = SavingsTransaction.objects.select_related("group", "member", "recorded_by").all()
    group_id = request.GET.get("group")
    if group_id:
        qs = qs.filter(group_id=group_id)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    transaction_type = request.GET.get("transaction_type", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if q:
        qs = qs.filter(Q(member__first_name__icontains=q) | Q(member__last_name__icontains=q) | Q(transaction_ref__icontains=q) | Q(receipt_no__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if transaction_type:
        qs = qs.filter(transaction_type=transaction_type)
    if start:
        qs = qs.filter(transaction_date__gte=start)
    if end:
        qs = qs.filter(transaction_date__lte=end)
    return render(request, "vsla/savings_list.html", {"transactions": qs[:250], "groups": VSLAGroup.objects.order_by("name"), "q": q, "selected_group": group_id, "selected_status": status, "selected_type": transaction_type, "start": start, "end": end, "statuses": LedgerEntry.Status.choices, "transaction_types": SavingsTransaction.Type.choices, "title": "Weekly Savings Ledger"})


@vsla_access_required
def savings_create(request):
    initial = {}
    member_id = request.GET.get("member")
    group_id = request.GET.get("group")
    if member_id:
        selected_member = VSLAMember.objects.select_related("group").filter(pk=member_id).first()
        if selected_member:
            initial.update(member=selected_member.pk, group=selected_member.group_id)
    elif group_id:
        initial["group"] = group_id
    form = SavingsTransactionForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.recorded_by = request.user
        try:
            obj.full_clean()
            obj.save()
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"Savings transaction {obj.transaction_ref} recorded.")
            return redirect("vsla:savings")
    return render(request, "vsla/form.html", {"form": form, "title": "Record Weekly Savings", "eyebrow": "SAVINGS LEDGER", "cancel_url": "vsla:savings"})


@vsla_access_required
def loan_list(request):
    qs = Loan.objects.select_related("group", "member", "reviewed_by").all()
    status = request.GET.get("status")
    group_id = request.GET.get("group", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if status:
        qs = qs.filter(status=status)
    if group_id:
        qs = qs.filter(group_id=group_id)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(loan_no__icontains=q) | Q(member__first_name__icontains=q) | Q(member__last_name__icontains=q))
    if start:
        qs = qs.filter(application_date__gte=start)
    if end:
        qs = qs.filter(application_date__lte=end)
    return render(request, "vsla/loan_list.html", {"loans": qs[:250], "q": q, "selected_status": status, "selected_group": group_id, "start": start, "end": end, "groups": VSLAGroup.objects.order_by("name"), "statuses": Loan.Status.choices, "title": "Loan Portfolio"})


@vsla_access_required
def loan_create(request):
    initial = {}
    member_id = request.GET.get("member")
    group_id = request.GET.get("group")
    if member_id:
        selected_member = VSLAMember.objects.select_related("group").filter(pk=member_id).first()
        if selected_member:
            initial.update(member=selected_member.pk, group=selected_member.group_id)
    elif group_id:
        initial["group"] = group_id
    form = LoanForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.submitted_by = request.user
        obj.save()
        messages.success(request, f"Loan application {obj.loan_no} saved as draft.")
        return redirect("vsla:loan_detail", loan_no=obj.loan_no)
    return render(request, "vsla/form.html", {"form": form, "title": "New Loan Application", "eyebrow": "CREDIT MANAGEMENT", "cancel_url": "vsla:loans"})


@vsla_access_required
def loan_detail(request, loan_no):
    loan = get_object_or_404(Loan.objects.select_related("group", "member"), loan_no=loan_no)
    repayments = loan.repayments.filter(status=LedgerEntry.Status.POSTED).order_by("-transaction_date")
    return render(request, "vsla/loan_detail.html",
                  {"loan": loan, "repayments": repayments, "repayment_form": LoanRepaymentForm(), "title": loan.loan_no})


@vsla_access_required
@require_POST
def loan_submit(request, loan_no):
    loan = get_object_or_404(Loan, loan_no=loan_no)
    if loan.status != Loan.Status.DRAFT:
        messages.error(request, "Only draft loan applications can be submitted.")
    else:
        loan.status = Loan.Status.SUBMITTED
        loan.save(update_fields=["status", "updated_at"])
        messages.success(request, "Loan application submitted for review.")
    return redirect("vsla:loan_detail", loan_no=loan_no)


@vsla_access_required
@require_POST
def loan_decision(request, loan_no):
    if not (request.user.has_perm("vsla.review_vsla_loan") or request.user.has_perm("vsla.approve_vsla_loan") or request.user.is_superuser or request.user.is_staff):
        return HttpResponseForbidden("You do not have permission to review loans.")
    loan = get_object_or_404(Loan, loan_no=loan_no)
    decision = request.POST.get("decision")
    comment = request.POST.get("comment", "").strip()
    if decision in {"approve", "reject"} and loan.status != Loan.Status.SUBMITTED:
        messages.error(request, "Only submitted loan applications can be reviewed.")
    elif decision == "approve":
        try:
            amount = Decimal(request.POST.get("approved_amount") or loan.requested_amount)
            if amount <= 0 or amount > loan.requested_amount:
                raise ValueError
        except (ValueError, ArithmeticError):
            messages.error(request, "Enter a valid approved amount not exceeding the requested amount.")
            return redirect("vsla:loan_detail", loan_no=loan_no)
        loan.approved_amount = amount
        loan.status = Loan.Status.APPROVED
        loan.reviewed_by = request.user
        loan.reviewed_at = timezone.now()
        loan.decision_comment = comment
        loan.save()
        messages.success(request, "Loan approved. Record disbursement when funds are issued.")
    elif decision == "reject":
        loan.status = Loan.Status.REJECTED
        loan.reviewed_by = request.user
        loan.reviewed_at = timezone.now()
        loan.decision_comment = comment
        loan.save()
        messages.success(request, "Loan application rejected.")
    elif decision == "disburse":
        if loan.status != Loan.Status.APPROVED:
            messages.error(request, "Only approved loans can be disbursed.")
        else:
            loan.status = Loan.Status.DISBURSED
            loan.disbursed_by = request.user
            loan.disbursed_at = timezone.now()
            loan.due_date = timezone.localdate() + timedelta(weeks=loan.duration_weeks)
            loan.save()
            messages.success(request, "Loan marked as disbursed.")
    else:
        messages.error(request, "Unknown loan decision.")
    return redirect("vsla:loan_detail", loan_no=loan_no)


@vsla_access_required
@require_POST
def repayment_create(request, loan_no):
    loan = get_object_or_404(Loan, loan_no=loan_no)
    form = LoanRepaymentForm(request.POST)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.loan = loan
        obj.recorded_by = request.user
        try:
            obj.full_clean()
            obj.save()
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, "Loan repayment recorded.")
    else:
        messages.error(request, "Please correct the repayment details.")
    return redirect("vsla:loan_detail", loan_no=loan_no)


@vsla_access_required
def meeting_list(request):
    meetings = VSLA_Meeting.objects.select_related("group", "recorded_by").all()
    q = request.GET.get("q", "").strip()
    group_id = request.GET.get("group", "")
    status = request.GET.get("status", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if q:
        meetings = meetings.filter(Q(group__name__icontains=q) | Q(venue__icontains=q) | Q(meeting_number__icontains=q))
    if group_id:
        meetings = meetings.filter(group_id=group_id)
    if status:
        meetings = meetings.filter(status=status)
    if start:
        meetings = meetings.filter(meeting_date__gte=start)
    if end:
        meetings = meetings.filter(meeting_date__lte=end)
    return render(request, "vsla/meeting_list.html", {"meetings": meetings[:200], "groups": VSLAGroup.objects.order_by("name"), "q": q, "selected_group": group_id, "selected_status": status, "start": start, "end": end, "statuses": VSLA_Meeting.Status.choices, "title": "Group Meetings"})


@vsla_access_required
def meeting_create(request):
    initial = {}
    group_id = request.GET.get("group")
    if group_id and VSLAGroup.objects.filter(pk=group_id).exists():
        initial["group"] = group_id
    form = VSLA_MeetingForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.recorded_by = request.user
        obj.save()
        messages.success(request, "Meeting recorded.")
        return redirect("vsla:meetings")
    return render(request, "vsla/form.html", {"form": form, "title": "Record Group Meeting", "eyebrow": "MEETING MANAGEMENT", "cancel_url": "vsla:meetings"})


@vsla_access_required
def social_fund_list(request):
    txs = SocialFundTransaction.objects.select_related("group", "member", "recorded_by").all()
    q = request.GET.get("q", "").strip()
    group_id = request.GET.get("group", "")
    status = request.GET.get("status", "")
    transaction_type = request.GET.get("transaction_type", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if q:
        txs = txs.filter(Q(transaction_ref__icontains=q) | Q(member__first_name__icontains=q) | Q(member__last_name__icontains=q) | Q(beneficiary_name__icontains=q))
    if group_id:
        txs = txs.filter(group_id=group_id)
    if status:
        txs = txs.filter(status=status)
    if transaction_type:
        txs = txs.filter(transaction_type=transaction_type)
    if start:
        txs = txs.filter(transaction_date__gte=start)
    if end:
        txs = txs.filter(transaction_date__lte=end)
    return render(request, "vsla/social_fund_list.html", {"transactions": txs[:250], "groups": VSLAGroup.objects.order_by("name"), "q": q, "selected_group": group_id, "selected_status": status, "selected_type": transaction_type, "start": start, "end": end, "statuses": LedgerEntry.Status.choices, "transaction_types": SocialFundTransaction.Type.choices, "title": "Social Fund Ledger"})


@vsla_access_required
def social_fund_create(request):
    initial = {}
    member_id = request.GET.get("member")
    group_id = request.GET.get("group")
    if member_id:
        selected_member = VSLAMember.objects.select_related("group").filter(pk=member_id).first()
        if selected_member:
            initial.update(member=selected_member.pk, group=selected_member.group_id)
    elif group_id:
        initial["group"] = group_id
    form = SocialFundTransactionForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.recorded_by = request.user
        try:
            obj.full_clean()
            obj.save()
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Social fund transaction recorded.")
            return redirect("vsla:social_fund")
    return render(request, "vsla/form.html", {"form": form, "title": "Record Social Fund Transaction", "eyebrow": "SOCIAL PROTECTION", "cancel_url": "vsla:social_fund"})


@vsla_access_required
def share_out_summary(request):
    groups = VSLAGroup.objects.all()
    group_id = request.GET.get("group")
    group = groups.filter(pk=group_id).first() if group_id else groups.first()
    rows = []
    total_shares = Decimal("0")
    share_value = Decimal("0")
    if group:
        members = group.members.all()
        posted = group.savings_transactions.filter(status=LedgerEntry.Status.POSTED)
        deposits = posted.filter(transaction_type=SavingsTransaction.Type.DEPOSIT).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        outflows = posted.filter(transaction_type__in=[SavingsTransaction.Type.WITHDRAWAL, SavingsTransaction.Type.SHARE_OUT]).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        pool = max(Decimal("0"), deposits - outflows)
        member_rows = []
        for member in members:
            saved = posted.filter(member=member, transaction_type=SavingsTransaction.Type.DEPOSIT).aggregate(v=Sum("amount"))["v"] or Decimal("0")
            shares = saved / group.weekly_share_value if group.weekly_share_value else Decimal("0")
            loans = member.loans.filter(status__in=[Loan.Status.DISBURSED, Loan.Status.DEFAULTED])
            loan_balance = sum((loan.outstanding_balance for loan in loans), Decimal("0"))
            member_rows.append({"member": member, "shares": shares, "loan_balance": loan_balance})
            total_shares += shares
        share_value = pool / total_shares if total_shares else Decimal("0")
        for item in member_rows:
            received = item["shares"] * share_value
            item.update(total_received=received, net_amount=max(Decimal("0"), received - item["loan_balance"]))
        rows = member_rows
    return render(request, "vsla/share_out_summary.html", {"groups": groups, "group": group, "rows": rows, "total_shares": total_shares, "share_value": share_value, "total_payout": sum((row["net_amount"] for row in rows), Decimal("0"))})


@vsla_access_required
def challenge_story_list(request):
    group_id = request.GET.get("group")
    entries = VSLAChallengeStory.objects.select_related("group", "recorded_by")
    q = request.GET.get("q", "").strip()
    entry_type = request.GET.get("entry_type", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if group_id:
        entries = entries.filter(group_id=group_id)
    if q:
        entries = entries.filter(Q(member_or_group_name__icontains=q) | Q(story_or_challenge__icontains=q) | Q(action_or_impact__icontains=q) | Q(comments__icontains=q))
    if entry_type:
        entries = entries.filter(entry_type=entry_type)
    if start:
        entries = entries.filter(entry_date__gte=start)
    if end:
        entries = entries.filter(entry_date__lte=end)
    return render(request, "vsla/challenge_story_list.html", {"entries": entries[:250], "groups": VSLAGroup.objects.all(), "selected_group": group_id, "q": q, "selected_type": entry_type, "start": start, "end": end, "entry_types": VSLAChallengeStory.EntryType.choices})


@vsla_access_required
def challenge_story_create(request):
    initial = {}
    group_id = request.GET.get("group")
    if group_id and VSLAGroup.objects.filter(pk=group_id).exists():
        initial["group"] = group_id
    form = VSLAChallengeStoryForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.recorded_by = request.user
        obj.save()
        messages.success(request, "Challenge or success story recorded.")
        return redirect("vsla:challenge_stories")
    return render(request, "vsla/form.html", {"form": form, "title": "Record Challenge or Success Story", "eyebrow": "CHALLENGES & SUCCESS STORIES", "cancel_url": "vsla:challenge_stories"})


def _csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(rows)
    return response


@vsla_access_required
def export_groups(request):
    groups = VSLAGroup.objects.all()
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    district = request.GET.get("district", "").strip()
    if q:
        groups = groups.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(district__icontains=q))
    if status:
        groups = groups.filter(status=status)
    if district:
        groups = groups.filter(district__icontains=district)
    rows = [[g.code, g.name, g.project_name, g.donor_name, g.district, g.sub_county, g.parish_or_village, g.start_date, g.cycle_end_date, g.active_member_count, g.status] for g in groups]
    return _csv_response("aped-vsla-group-profile.csv", ["Group Code/ID", "Group Name", "Project", "Donor", "District", "Sub-county", "Parish/Village", "Cycle Start Date", "Cycle End Date", "Active Members", "Status"], rows)


@vsla_access_required
def export_members(request):
    members = VSLAMember.objects.select_related("group").all()
    q = request.GET.get("q", "").strip()
    group_id = request.GET.get("group", "")
    status = request.GET.get("status", "")
    gender = request.GET.get("gender", "")
    if q:
        members = members.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(member_no__icontains=q) | Q(phone__icontains=q))
    if group_id:
        members = members.filter(group_id=group_id)
    if status:
        members = members.filter(status=status)
    if gender:
        members = members.filter(gender=gender)
    rows = [[m.group.code, m.full_name, m.member_no, m.gender, m.joined_on, m.phone, m.village, m.status, m.consent_for_data] for m in members]
    return _csv_response("aped-vsla-member-registration.csv", ["Group Code/ID", "Member Name", "Member ID", "Gender", "Date Joined", "Phone Number", "Village", "Status", "Consent for Data"], rows)


@vsla_access_required
def export_savings(request):
    transactions = SavingsTransaction.objects.select_related("group", "member").all()
    q = request.GET.get("q", "").strip()
    group_id = request.GET.get("group", "")
    status = request.GET.get("status", "")
    transaction_type = request.GET.get("transaction_type", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if q:
        transactions = transactions.filter(Q(member__first_name__icontains=q) | Q(member__last_name__icontains=q) | Q(transaction_ref__icontains=q) | Q(receipt_no__icontains=q))
    if group_id:
        transactions = transactions.filter(group_id=group_id)
    if status:
        transactions = transactions.filter(status=status)
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    if start:
        transactions = transactions.filter(transaction_date__gte=start)
    if end:
        transactions = transactions.filter(transaction_date__lte=end)
    rows = [[t.transaction_date, t.group.code, t.member.full_name, t.member.member_no, t.amount, t.transaction_type, t.week_ending, t.receipt_no, t.status] for t in transactions]
    return _csv_response("aped-vsla-savings-record.csv", ["Meeting Date", "Group Code/ID", "Member Name", "Member ID", "Amount Saved", "Transaction Type", "Week Ending", "Receipt No.", "Status"], rows)


@vsla_access_required
def export_loans(request):
    loans = Loan.objects.select_related("group", "member").all()
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    group_id = request.GET.get("group", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if q:
        loans = loans.filter(Q(loan_no__icontains=q) | Q(member__first_name__icontains=q) | Q(member__last_name__icontains=q))
    if status:
        loans = loans.filter(status=status)
    if group_id:
        loans = loans.filter(group_id=group_id)
    if start:
        loans = loans.filter(application_date__gte=start)
    if end:
        loans = loans.filter(application_date__lte=end)
    rows = [[l.group.code, l.member.full_name, l.member.member_no, l.loan_no, l.requested_amount, l.approved_amount, l.application_date, l.due_date, l.interest_rate, l.duration_weeks, l.purpose, l.status] for l in loans]
    return _csv_response("aped-vsla-loan-application-approval.csv", ["Group Code/ID", "Member Name", "Member ID", "Loan ID", "Loan Amount Requested", "Approved Amount", "Date of Request", "Due Date", "Interest Rate (%)", "Repayment Period (Weeks)", "Purpose", "Status"], rows)


@vsla_access_required
def export_meetings(request):
    meetings = VSLA_Meeting.objects.select_related("group", "recorded_by").all()
    q = request.GET.get("q", "").strip()
    group_id = request.GET.get("group", "")
    status = request.GET.get("status", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if q:
        meetings = meetings.filter(Q(group__name__icontains=q) | Q(venue__icontains=q) | Q(meeting_number__icontains=q))
    if group_id:
        meetings = meetings.filter(group_id=group_id)
    if status:
        meetings = meetings.filter(status=status)
    if start:
        meetings = meetings.filter(meeting_date__gte=start)
    if end:
        meetings = meetings.filter(meeting_date__lte=end)
    rows = [[m.meeting_date, m.group.code, m.group.name, m.meeting_number, m.venue, m.get_status_display(), m.members_present, m.members_absent] for m in meetings]
    return _csv_response("aped-vsla-meetings.csv", ["Date", "Group Code/ID", "Group Name", "Meeting No.", "Venue", "Status", "Members Present", "Members Absent"], rows)


@vsla_access_required
def export_social_fund(request):
    transactions = SocialFundTransaction.objects.select_related("group", "member").all()
    q = request.GET.get("q", "").strip()
    group_id = request.GET.get("group", "")
    status = request.GET.get("status", "")
    transaction_type = request.GET.get("transaction_type", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if q:
        transactions = transactions.filter(Q(transaction_ref__icontains=q) | Q(member__first_name__icontains=q) | Q(member__last_name__icontains=q) | Q(beneficiary_name__icontains=q))
    if group_id:
        transactions = transactions.filter(group_id=group_id)
    if status:
        transactions = transactions.filter(status=status)
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    if start:
        transactions = transactions.filter(transaction_date__gte=start)
    if end:
        transactions = transactions.filter(transaction_date__lte=end)
    rows = [[t.transaction_date, t.transaction_ref, t.group.code, t.group.name, t.member.full_name if t.member_id else t.beneficiary_name, t.get_transaction_type_display(), t.amount, t.get_status_display()] for t in transactions]
    return _csv_response("aped-vsla-social-fund.csv", ["Date", "Reference", "Group Code/ID", "Group Name", "Member/Beneficiary", "Transaction Type", "Amount", "Status"], rows)


@vsla_access_required
def export_challenge_stories(request):
    entries = VSLAChallengeStory.objects.select_related("group").all()
    group_id = request.GET.get("group", "")
    q = request.GET.get("q", "").strip()
    entry_type = request.GET.get("entry_type", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if group_id:
        entries = entries.filter(group_id=group_id)
    if q:
        entries = entries.filter(Q(member_or_group_name__icontains=q) | Q(story_or_challenge__icontains=q) | Q(action_or_impact__icontains=q) | Q(comments__icontains=q))
    if entry_type:
        entries = entries.filter(entry_type=entry_type)
    if start:
        entries = entries.filter(entry_date__gte=start)
    if end:
        entries = entries.filter(entry_date__lte=end)
    rows = [[e.entry_date, e.group.name, e.member_or_group_name or e.group.name, e.get_entry_type_display(), e.story_or_challenge, e.action_or_impact, e.comments] for e in entries]
    return _csv_response("aped-vsla-challenges-stories.csv", ["Date", "Group", "Member/Group Name", "Type", "Challenge or Success Story", "Action/Impact", "Comments"], rows)


@vsla_access_required
def export_workbook(request):
    workbook = Workbook()
    workbook.remove(workbook.active)

    def sheet(title, headers, rows):
        ws = workbook.create_sheet(title[:31])
        ws.append(headers)
        for row in rows:
            ws.append(row)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]:
            cell.font = cell.font.copy(bold=True, color="FFFFFF")
            cell.fill = cell.fill.copy(fill_type="solid", fgColor="245B48")
        for column in ws.columns:
            letter = column[0].column_letter
            ws.column_dimensions[letter].width = min(max(max(len(str(c.value or "")) for c in column) + 2, 12), 32)
        return ws

    group_id = request.GET.get("group", "")
    group_status = request.GET.get("group_status", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    groups_qs = VSLAGroup.objects.all()
    if group_id:
        groups_qs = groups_qs.filter(pk=group_id)
    if group_status:
        groups_qs = groups_qs.filter(status=group_status)
    group_ids = groups_qs.values("pk")
    members_qs = VSLAMember.objects.select_related("group").filter(group_id__in=group_ids)
    meetings_qs = VSLA_Meeting.objects.select_related("group").filter(group_id__in=group_ids)
    attendance_qs = MeetingAttendance.objects.select_related("meeting", "member").filter(meeting__group_id__in=group_ids)
    savings_qs = SavingsTransaction.objects.select_related("group", "member").filter(group_id__in=group_ids)
    loans_qs = Loan.objects.select_related("group", "member").filter(group_id__in=group_ids)
    repayments_qs = LoanRepayment.objects.select_related("loan", "loan__member").filter(loan__group_id__in=group_ids)
    if start:
        meetings_qs = meetings_qs.filter(meeting_date__gte=start)
        savings_qs = savings_qs.filter(transaction_date__gte=start)
        loans_qs = loans_qs.filter(application_date__gte=start)
        repayments_qs = repayments_qs.filter(transaction_date__gte=start)
    if end:
        meetings_qs = meetings_qs.filter(meeting_date__lte=end)
        savings_qs = savings_qs.filter(transaction_date__lte=end)
        loans_qs = loans_qs.filter(application_date__lte=end)
        repayments_qs = repayments_qs.filter(transaction_date__lte=end)
    groups = list(groups_qs)
    members = list(members_qs)
    meetings = list(meetings_qs)
    attendance = list(attendance_qs)
    savings = list(savings_qs)
    loans = list(loans_qs)
    repayments = list(repayments_qs)
    share_outs = [t for t in savings if t.transaction_type == SavingsTransaction.Type.SHARE_OUT]
    stories_qs = VSLAChallengeStory.objects.select_related("group").filter(group_id__in=group_ids)
    if start:
        stories_qs = stories_qs.filter(entry_date__gte=start)
    if end:
        stories_qs = stories_qs.filter(entry_date__lte=end)
    stories = list(stories_qs)

    sheet("Group Profile", ["Group Code/ID", "Group Name", "Project", "Donor", "District", "Sub-county", "Parish/Village", "Cycle Start Date", "Cycle End Date", "Active Members", "Status"], [[g.code, g.name, g.project_name, g.donor_name, g.district, g.sub_county, g.parish_or_village, g.start_date, g.cycle_end_date, g.active_member_count, g.status] for g in groups])
    sheet("Member Registration", ["Group Code/ID", "Group Name", "Member Name", "Member ID", "Gender", "Age/Date of Birth", "Phone Number", "Role", "Date Joined", "Signature/Consent"], [[m.group.code, m.group.name, m.full_name, m.member_no, m.gender, m.date_of_birth, m.phone, "", m.joined_on, "Yes" if m.consent_for_data else ""] for m in members])
    attendance_rows = []
    for meeting in meetings:
        entries = list(meeting.attendance.all()) or [None]
        for entry in entries:
            attendance_rows.append([
                meeting.meeting_date,
                meeting.meeting_number,
                meeting.group.name,
                "Yes" if meeting.chairperson_present else "No" if meeting.chairperson_present is not None else "",
                "Yes" if meeting.secretary_present else "No" if meeting.secretary_present is not None else "",
                meeting.members_present,
                meeting.member_names_or_ids,
                meeting.members_absent,
                meeting.notes,
                entry.member.full_name if entry else "",
                ("Yes" if entry.present else "No") if entry else "",
                entry.remarks if entry else "",
            ])
    sheet("Attendance Register", ["Date", "Meeting No.", "Group Name", "Chairperson Present? (Y/N)", "Secretary Present? (Y/N)", "Members Present", "List Names or IDs", "Members Absent", "Notes", "Individual Member", "Present", "Remarks"], attendance_rows)
    sheet("Savings Record", ["Meeting Date", "Member Name", "Member ID", "Amount Saved", "Transaction Type", "Total Shares", "Receipt No."], [[t.transaction_date, t.member.full_name, t.member.member_no, t.amount, t.get_transaction_type_display(), "", t.receipt_no] for t in savings])
    sheet("Loan Application", ["Member Name", "Member ID", "Loan ID", "Loan Amount Requested", "Approved Amount", "Purpose", "Date of Request", "Repayment Period (Weeks)", "Interest Rate (%)", "Group Approval/Status"], [[l.member.full_name, l.member.member_no, l.loan_no, l.requested_amount, l.approved_amount, l.purpose, l.application_date, l.duration_weeks, l.interest_rate, l.get_status_display()] for l in loans])
    sheet("Loan Repayment", ["Member Name", "Loan ID", "Loan Amount", "Repayment Date", "Amount Paid", "Balance Remaining", "Notes"], [[r.loan.member.full_name, r.loan.loan_no, r.loan.principal, r.transaction_date, r.amount, r.loan.outstanding_balance, r.notes] for r in repayments])
    sheet("Share-Out Summary", ["Member Name", "Member ID", "Share-Out Date", "Amount Paid Out", "Receipt No.", "Comments"], [[t.member.full_name, t.member.member_no, t.transaction_date, t.amount, t.receipt_no, t.notes] for t in share_outs])
    sheet("Monitoring & Evaluation", ["Group Code/ID", "Group Name", "Active Members", "Total Savings", "Loans Distributed", "Loans Repaid", "Defaulted Loans", "Meetings Recorded"], [[g.code, g.name, g.active_member_count, g.total_savings, sum((l.principal for l in loans if l.group_id == g.id and l.status in [Loan.Status.DISBURSED, Loan.Status.CLOSED]), Decimal("0")), sum((r.amount for r in repayments if r.loan.group_id == g.id), Decimal("0")), sum((l.principal for l in loans if l.group_id == g.id and l.status == Loan.Status.DEFAULTED), Decimal("0")), sum((1 for m in meetings if m.group_id == g.id))] for g in groups])
    sheet("Challenges & Stories", ["Date", "Member/Group Name", "Challenge or Success Story", "Action Taken or Impact", "Comments"], [[entry.entry_date, entry.member_or_group_name or entry.group.name, f"{entry.get_entry_type_display()}: {entry.story_or_challenge}", entry.action_or_impact, entry.comments] for entry in stories])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="aped-vsla-workbook-package.xlsx"'
    workbook.save(response)
    return response

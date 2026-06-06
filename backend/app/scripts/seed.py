"""Authentic baseline data for a regional newspaper CRM.

After a clean DB (e.g. `docker compose down -v && up -d && alembic upgrade head`)
this script populates the data a sales/circulation/accounts desk would actually
see on day one: a dozen real-style advertisers across categories, sixteen
subscribers spread over four delivery areas, a handful of classifieds in
various states, four open complaints covering both routine and sensitive
triage paths, and three live DIPR-style tenders.

Idempotent — every insert is keyed on a unique field, so re-running adds
nothing duplicate.

Run inside the backend container:
    python -m app.scripts.seed
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.engines.pricing import quote
from app.models.advertiser import (
    Advertiser,
    AdvertiserStatus,
    Contract,
    ContractStatus,
)
from app.models.classified import Classified, ClassifiedStatus
from app.models.complaint import (
    Complaint,
    ComplaintChannel,
    ComplaintStatus,
    ComplaintTriage,
)
from app.models.subscriber import (
    AreaReturns,
    Plan,
    Subscriber,
    SubscriberStatus,
    Subscription,
    SubscriptionStatus,
)
from app.models.tender import GovTender, TenderStatus
from app.models.user import User, UserRole
from app.services.churn import recompute_churn

TODAY = date.today()


# ---------------------------------------------------------------------------
# Users — newsroom + business office staff. Credentials kept identical to
# README/login page so existing docs and e2e tests keep working.
# ---------------------------------------------------------------------------
USERS = [
    ("Admin", "admin@example.com", "admin123", UserRole.ADMIN),
    ("Anjali Rao", "sales@example.com", "sales123", UserRole.SALES),
    ("Hari Prasad", "circ@example.com", "circ123", UserRole.CIRCULATION),
    ("Suresh Kumar", "accounts@example.com", "accounts123", UserRole.ACCOUNTS),
]


# ---------------------------------------------------------------------------
# Advertisers — 12 businesses across the categories a regional daily sells to.
# Contracts are tuned so the churn engine lands a mix of bands and so a few
# fall inside the renewal-reminder windows (1/3/7/14 days out).
# Contract tuple: (start_offset_days, end_offset_days, value, slots)
# ---------------------------------------------------------------------------
ADVERTISERS: list[tuple] = [
    # --- low churn -----------------------------------------------------------
    ("Sahyadri Motors", "Auto", "Rajesh Patel",
        "+919812300001", "rajesh@sahyadrimotors.in",
        "2400000.00", "5.00", "68.00", AdvertiserStatus.ACTIVE,
        [(-300, 65, "600000.00", 12)]),
    ("Patel Jewellers", "Jewellery", "Anita Patel",
        "+919812300002", "accounts@pateljewellers.in",
        "1800000.00", "12.00", "75.00", AdvertiserStatus.ACTIVE,
        [(-90, 275, "450000.00", 8)]),
    ("Apex Hospital", "Healthcare", "Dr Neha Iyer",
        "+919812300003", "marketing@apexhospital.in",
        "3200000.00", "8.00", "72.00", AdvertiserStatus.ACTIVE,
        [(-60, 305, "800000.00", 14)]),
    ("Patanjali Wellness", "Health & Wellness", "Sadhana Joshi",
        "+919812300004", "info@patanjaliwellness.in",
        "600000.00", "15.00", "80.00", AdvertiserStatus.ACTIVE,
        [(-60, 305, "150000.00", 4)]),

    # --- mid band ------------------------------------------------------------
    ("Vidya Bhawan Classes", "Education", "Dr Suresh Mehta",
        "+919812300005", "info@vidyabhawan.edu.in",
        "960000.00", "-25.00", "35.00", AdvertiserStatus.ACTIVE,
        [(-330, 28, "240000.00", 6)]),  # contract expiring soon + softening spend
    ("Aakash Coaching", "Education", "Priya Nair",
        "+919812300007", "info@aakashcoaching.in",
        "1200000.00", "-20.00", "48.00", AdvertiserStatus.ACTIVE,
        [(-275, 14, "300000.00", 7)]),  # 14d renewal window
    ("Greenleaf Restaurant", "Food & Beverage", "Vikram Singh",
        "+919812300008", "vikram@greenleaf.in",
        "450000.00", "3.00", "55.00", AdvertiserStatus.ACTIVE,
        [(-180, 7, "110000.00", 4)]),   # 7d renewal window
    ("Sharma Electronics", "Electronics", "Vinod Sharma",
        "+919812300006", "vinod@sharmaelec.in",
        "780000.00", "-8.00", "52.00", AdvertiserStatus.ACTIVE,
        [(-150, 215, "195000.00", 5)]),

    # --- high churn ----------------------------------------------------------
    ("Sunrise Builders", "Real estate", "Karan Mehta",
        "+919812300009", "office@sunrisebuilders.in",
        "2100000.00", "-55.00", "18.00", AdvertiserStatus.ACTIVE,
        [(-340, 5, "525000.00", 10)]),
    ("Shubham Properties", "Real estate", "Manish Shubham",
        "+919812300010", "manish@shubhamprop.in",
        "1500000.00", "-45.00", "20.00", AdvertiserStatus.ACTIVE,
        [(-380, -5, "375000.00", 6)]),  # contract already expired

    # --- prospects / no contract --------------------------------------------
    ("Indus Bookstore", "Retail", "Manoj Verma",
        "+919812300011", "indus@books.in",
        "300000.00", "0.00", "60.00", AdvertiserStatus.ACTIVE,
        []),
    ("Rajwada Sweets", "Food & Beverage", "Rakesh Joshi",
        "+919812300012", "rakesh@rajwadasweets.in",
        "520000.00", "18.00", "70.00", AdvertiserStatus.PROSPECT,
        []),
]


# ---------------------------------------------------------------------------
# Subscribers — 16 households across 4 delivery areas. Plans, miss-counts and
# renew dates are spread so the dashboard, at-risk filter and renewal-reminder
# job all have realistic work to do.
# Subscription tuple: (start_offset, renew_offset, monthly_price)
# ---------------------------------------------------------------------------
SUBSCRIBERS: list[tuple] = [
    # Vijay Nagar
    ("Anil Kumar Sharma", "+919823100001", "Vijay Nagar", "12 Sapna Sangeeta Road",
        Plan.DAILY, 0, (-180, 20, "350.00")),
    ("Sunita Patel", "+919823100002", "Vijay Nagar", "204 Ratnamani Apartments",
        Plan.DAILY, 0, (-200, 50, "350.00")),
    ("Ravi Yadav", "+919823100003", "Vijay Nagar", "67 Nakshatra Colony",
        Plan.WEEKEND, 1, (-90, 7, "180.00")),       # 7d window
    ("Pooja Joshi", "+919823100004", "Vijay Nagar", "B-9 Krishna Towers",
        Plan.DAILY, 0, (-365, 120, "350.00")),

    # Palasia
    ("Vikram Singh Rajput", "+919823100005", "Palasia", "House 41, Shri Nagar",
        Plan.DAILY, 0, (-240, 60, "350.00")),
    ("Meera Iyer", "+919823100006", "Palasia", "303 Aishwarya Apartments",
        Plan.SUNDAY_ONLY, 2, (-150, 14, "120.00")),  # at-risk + 14d window
    ("Arjun Mehta", "+919823100007", "Palasia", "8 Manorama Ganj",
        Plan.DAILY, 0, (-100, 30, "350.00")),

    # South Tukoganj
    ("Sneha Kulkarni", "+919823100008", "South Tukoganj", "21 Patel Bridge Road",
        Plan.WEEKEND, 0, (-60, 90, "180.00")),
    ("Devendra Choudhary", "+919823100009", "South Tukoganj", "A-12 Sai Plaza",
        Plan.DAILY, 0, (-220, 45, "350.00")),
    ("Lata Joshi", "+919823100010", "South Tukoganj", "7 Race Course Road",
        Plan.DAILY, 1, (-300, 3, "350.00")),         # 3d window
    ("Naveen Pillai", "+919823100011", "South Tukoganj", "144 RNT Marg",
        Plan.SUNDAY_ONLY, 0, (-90, 80, "120.00")),

    # MG Road
    ("Kamla Devi Bansal", "+919823100012", "MG Road", "Old Building #4, MG Road",
        Plan.DAILY, 0, (-450, 150, "350.00")),
    ("Manoj Kumar Tiwari", "+919823100013", "MG Road", "23 Yashwant Plaza",
        Plan.DAILY, 0, (-180, 1, "350.00")),         # 1d window
    ("Rashmi Agarwal", "+919823100014", "MG Road", "5 Treasure Island Apartments",
        Plan.WEEKEND, 0, (-120, 75, "180.00")),

    # Saket Nagar
    ("Harish Chand Verma", "+919823100015", "Saket Nagar", "Plot 88, Saket Phase II",
        Plan.DAILY, 3, (-365, -5, "350.00")),        # overdue + 3 missed
    ("Geeta Pandey", "+919823100016", "Saket Nagar", "C-22 Saket Square",
        Plan.DAILY, 0, (-60, 200, "350.00")),
]


# Historical % unsold per area — seeds the print-run forecast.
AREA_RETURNS = [
    ("Vijay Nagar", "3.50"),
    ("Palasia", "5.00"),
    ("South Tukoganj", "4.20"),
    ("MG Road", "2.80"),
    ("Saket Nagar", "6.50"),
]


# ---------------------------------------------------------------------------
# Classifieds — six real-style ads across the status flow.
# Tuple: (customer_name, phone, text, category, duration_days, status, publish_offset)
# ---------------------------------------------------------------------------
CLASSIFIEDS: list[tuple] = [
    ("Mrs Reshma Khanna", "+919876500001",
        "Suitable alliance invited for Brahmin girl, 26 yrs, B.E., software engineer, "
        "working at IT firm in Pune. Please send biodata and horoscope to family.",
        "MATRIMONIAL", 7, ClassifiedStatus.PUBLISHED, -2),
    ("Mr Rakesh Bhandari", "+919876500002",
        "2 BHK flat available for rent in Vijay Nagar near International School. "
        "Semi-furnished, lift, 24x7 water. Rent 18,000 per month. Family only.",
        "PROPERTY", 5, ClassifiedStatus.PUBLISHED, -1),
    ("Mr Ajay Kumar", "+919876500003",
        "Maruti Alto K10 2019 model, white, second owner, 28,500 kms, all four new "
        "tyres, insurance valid. Asking price 2.85 lakh negotiable.",
        "VEHICLES", 3, ClassifiedStatus.PAID, 1),
    ("Mrs Anita Sharma", "+919876500004",
        "Receptionist required for new dental clinic in Saket Nagar. Female "
        "candidates preferred, computer knowledge essential. Salary 12k-15k. "
        "Walk in interview between 10 AM - 1 PM.",
        "JOBS", 2, ClassifiedStatus.QUOTED, None),
    ("Pandit family", "+919876500005",
        "We deeply mourn the passing of Late Shri Mohanlal Pandit on Tuesday. "
        "Antim sanskar performed. Prayer meeting on Sunday 4 PM at residence, "
        "11 Krishna Niwas, Palasia.",
        "OBITUARY", 1, ClassifiedStatus.PUBLISHED, 0),
    ("Mr Sudhir Mehta", "+919876500006",
        "Lost: Brown leather wallet near Rajwada Chowk on Wednesday evening. "
        "Contains important ID cards. Honest finder please contact, reward assured.",
        "GENERAL", 3, ClassifiedStatus.PAID, 2),
]


# ---------------------------------------------------------------------------
# Complaints — four authentic-sounding cases, left at triage=PENDING so the
# AI/engine path can be demonstrated by clicking "Run triage". Covers the
# routine, sensitive and ambiguous branches.
# ---------------------------------------------------------------------------
COMPLAINTS = [
    ("Anil Kumar Sharma", "+919823100001", "Vijay Nagar",
        "Paper has not been delivered for the last three days in our lane. "
        "I have spoken to the hawker twice but no improvement. Please look into it.",
        ComplaintChannel.PHONE),
    ("Meera Iyer", "+919823100006", "Palasia",
        "Please pause my subscription from the 15th of this month to the end of "
        "the month. The family is traveling to Bangalore for a wedding.",
        ComplaintChannel.WHATSAPP),
    ("Harish Chand Verma", "+919823100015", "Saket Nagar",
        "I was charged twice for the September renewal — once on the 2nd and "
        "again on the 5th. This is a billing dispute and I want a refund of "
        "the duplicate charge as soon as possible.",
        ComplaintChannel.EMAIL),
    ("Rashmi Agarwal", "+919823100014", "MG Road",
        "Wet copy received yesterday during the heavy rain. The paper was "
        "soaked and unreadable. Could you please send a replacement copy?",
        ComplaintChannel.PHONE),
]


# ---------------------------------------------------------------------------
# Government tenders — DIPR-style ad opportunities. Two fall inside the
# 14-day exception-queue window.
# ---------------------------------------------------------------------------
TENDERS = [
    ("Public Health — Dengue Awareness Campaign",
        "Department of Public Health", 7, "250000.00", TenderStatus.OPEN,
        "Vector-borne disease awareness campaign for monsoon season. Half-page "
        "colour preferred. Submit quote with sample mock-up."),
    ("Voter Awareness Drive 2026",
        "Office of the Chief Electoral Officer", 12, "450000.00", TenderStatus.OPEN,
        "Pre-election voter literacy series. 6-insertion package across Sunday "
        "editions. Empanelled vendors only."),
    ("Annual Tourism Promotion",
        "Department of Tourism", 32, "800000.00", TenderStatus.OPEN,
        "Multi-month tourism campaign for state heritage circuit. Display ads "
        "and supplements. Technical and financial bids required."),
]


# ---------------------------------------------------------------------------
# Per-table loaders. Every one is idempotent: keyed on a unique field so the
# script is safe to re-run without producing duplicates.
# ---------------------------------------------------------------------------

def _ensure_users(db) -> None:
    for name, email, password, role in USERS:
        if db.scalar(select(User).where(User.email == email)):
            continue
        db.add(User(
            name=name, email=email,
            password_hash=hash_password(password), role=role,
        ))
    db.flush()


def _ensure_advertisers(db) -> None:
    for (name, category, contact_name, phone, email,
         annual_value, spend_trend, open_rate, status, contracts) in ADVERTISERS:
        if db.scalar(select(Advertiser).where(Advertiser.name == name)):
            continue
        adv = Advertiser(
            name=name, category=category,
            contact_name=contact_name,
            contact_phone=phone, contact_email=email,
            annual_value=Decimal(annual_value),
            spend_trend=Decimal(spend_trend),
            proposal_open_rate=Decimal(open_rate),
            status=status,
        )
        db.add(adv)
        db.flush()
        for start_off, end_off, value, slots in contracts:
            db.add(Contract(
                advertiser_id=adv.id,
                start_date=TODAY + timedelta(days=start_off),
                end_date=TODAY + timedelta(days=end_off),
                value=Decimal(value),
                slots=slots,
                status=(
                    ContractStatus.EXPIRED if end_off < 0
                    else ContractStatus.ACTIVE
                ),
            ))
        db.flush()
        db.refresh(adv)
        recompute_churn(adv)
    db.flush()


def _ensure_subscribers(db) -> None:
    for (name, phone, area, address, plan, missed,
         (start_off, renew_off, monthly)) in SUBSCRIBERS:
        if db.scalar(select(Subscriber).where(Subscriber.phone == phone)):
            continue
        sub = Subscriber(
            name=name, phone=phone, area=area, address=address,
            plan=plan, status=SubscriberStatus.ACTIVE,
            missed_payments=missed,
        )
        db.add(sub)
        db.flush()
        db.add(Subscription(
            subscriber_id=sub.id,
            plan=plan,
            start_date=TODAY + timedelta(days=start_off),
            renew_date=TODAY + timedelta(days=renew_off),
            monthly_price=Decimal(monthly),
            status=SubscriptionStatus.ACTIVE,
        ))
    db.flush()


def _ensure_area_returns(db) -> None:
    for area, pct in AREA_RETURNS:
        if db.get(AreaReturns, area):
            continue
        db.add(AreaReturns(area=area, returns_pct=Decimal(pct)))


def _ensure_classifieds(db) -> None:
    for (name, phone, text, category, days, status, publish_off) in CLASSIFIEDS:
        existing = db.scalar(
            select(Classified).where(
                Classified.customer_phone == phone,
                Classified.text == text,
            )
        )
        if existing is not None:
            continue
        words = len([w for w in text.strip().split() if w])
        q = quote(words=words, category=category, duration_days=days, locale="IN")
        publish_date = None
        if publish_off is not None:
            publish_date = TODAY + timedelta(days=publish_off)
        db.add(Classified(
            customer_name=name, customer_phone=phone, text=text,
            word_count=words, category=category, duration_days=days,
            locale="IN", currency=q.currency,
            price_net=q.net, price_tax=q.tax, price_total=q.total,
            status=status, publish_date=publish_date,
        ))
    db.flush()


def _ensure_complaints(db) -> None:
    for (name, phone, area, text, channel) in COMPLAINTS:
        existing = db.scalar(
            select(Complaint).where(
                Complaint.subscriber_phone == phone,
                Complaint.text == text,
            )
        )
        if existing is not None:
            continue
        db.add(Complaint(
            subscriber_name=name, subscriber_phone=phone, area=area,
            text=text, channel=channel,
            triage=ComplaintTriage.PENDING,
            status=ComplaintStatus.OPEN,
        ))
    db.flush()


def _ensure_tenders(db) -> None:
    for (title, dept, deadline_off, value, status, notes) in TENDERS:
        if db.scalar(select(GovTender).where(GovTender.title == title)):
            continue
        db.add(GovTender(
            title=title, department=dept,
            deadline=TODAY + timedelta(days=deadline_off),
            est_value=Decimal(value), status=status, notes=notes,
        ))
    db.flush()


def run() -> None:
    with SessionLocal() as db:
        _ensure_users(db)
        _ensure_advertisers(db)
        _ensure_subscribers(db)
        _ensure_area_returns(db)
        _ensure_classifieds(db)
        _ensure_complaints(db)
        _ensure_tenders(db)
        db.commit()
    print("seed: done — authentic regional newspaper baseline")


if __name__ == "__main__":
    run()

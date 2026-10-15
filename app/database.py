"""Database connection and session management using SQLAlchemy 2.0."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# SQLite specific connect args to allow access across FastAPI worker threads
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency to provide a database session per request."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and seed default service recommendation rules."""
    from app import models  # noqa: F401 to ensure all models are imported
    Base.metadata.create_all(bind=engine)
    _seed_default_rules()


def _seed_default_rules():
    """Seed initial service recommendation rules if table is empty."""
    import json
    from app.models.rules import ServiceRule

    db = SessionLocal()
    try:
        count = db.query(ServiceRule).count()
        if count == 0:
            defaults = [
                {
                    "category_keyword": "barber",
                    "services": json.dumps([
                        "Website development & mobile booking",
                        "Online appointment calendar",
                        "Customer inquiry WhatsApp/chatbot",
                        "Automated SMS/WhatsApp appointment reminders",
                    ]),
                    "pitch_hook": "Allow clients to book hair cuts online 24/7 and reduce no-shows.",
                    "is_active": True,
                },
                {
                    "category_keyword": "restaurant",
                    "services": json.dumps([
                        "Modern responsive restaurant website",
                        "Direct online food ordering system",
                        "Table reservation chatbot",
                        "Digital QR menu & inventory tracking",
                        "AI voice agent for phone orders & table reservations",
                    ]),
                    "pitch_hook": "Save 20-30% on food aggregator commissions with direct online ordering.",
                    "is_active": True,
                },
                {
                    "category_keyword": "clinic",
                    "services": json.dumps([
                        "Modern medical clinic website",
                        "Online patient appointment scheduling",
                        "Patient FAQ & consultation triage chatbot",
                        "AI voice agent for administrative calls & hours info",
                    ]),
                    "pitch_hook": "Reduce front-desk call load by 60% with 24/7 automated booking.",
                    "is_active": True,
                },
                {
                    "category_keyword": "hotel",
                    "services": json.dumps([
                        "Direct room booking portal",
                        "Bilingual guest concierge chatbot",
                        "Hotel & amenities showcase website",
                        "AI voice-call agent for room inquiries and check-in info",
                    ]),
                    "pitch_hook": "Increase direct commission-free bookings and provide instant guest answers.",
                    "is_active": True,
                },
                {
                    "category_keyword": "school",
                    "services": json.dumps([
                        "Institutional school website & CMS",
                        "Admissions inquiry & campus tour chatbot",
                        "Student & parent information portal",
                        "Online fee payment & registration system",
                    ]),
                    "pitch_hook": "Streamline new student admissions and handle parent inquiries automatically.",
                    "is_active": True,
                },
                {
                    "category_keyword": "real estate",
                    "services": json.dumps([
                        "Property listing search portal",
                        "Lead capture chatbot with WhatsApp integration",
                        "Automated property tour booking calendar",
                        "AI voice agent for buyer qualification calls",
                    ]),
                    "pitch_hook": "Instantly qualify buyers and schedule viewings even outside office hours.",
                    "is_active": True,
                },
            ]
            for d in defaults:
                rule = ServiceRule(**d)
                db.add(rule)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Warning: Failed to seed default service rules: {e}")
    finally:
        db.close()

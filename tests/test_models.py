"""Test database models and relationships."""

import pytest
from datetime import date
from sqlalchemy.exc import IntegrityError
from app.models.business import Business, BusinessContact
from app.models.lead import SavedLead, LeadList, LeadListItem
from app.models.task import FollowUpTask
from app.models.rules import ServiceRule
from app.models.audit import WebsiteAudit


def test_create_business_and_contacts(db_session):
    """Test business creation, unique constraint, and contacts relationship."""
    b = Business(
        source="osm",
        source_id="osm:node/1001",
        name="Royal Barber Shop",
        category="barbershop",
        city="Lahore",
        country="Pakistan",
        website="https://royalbarbershop.example.com",
        phone="+923001234567",
        opportunity_priority="High Priority",
        opportunity_score=85,
    )
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)

    assert b.id is not None
    assert b.name == "Royal Barber Shop"

    contact = BusinessContact(
        business_id=b.id,
        type="phone",
        value="+923001234567",
        source="osm",
    )
    db_session.add(contact)
    db_session.commit()

    assert len(b.contacts) == 1
    assert b.contacts[0].value == "+923001234567"


def test_business_source_unique_constraint(db_session):
    """Ensure duplicate source_id cannot be inserted for same source."""
    b1 = Business(source="osm", source_id="osm:node/999", name="Shop A")
    b2 = Business(source="osm", source_id="osm:node/999", name="Shop B")

    db_session.add(b1)
    db_session.commit()

    db_session.add(b2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_save_lead_and_tasks(db_session):
    """Test creating a saved lead with follow-up tasks and custom lists."""
    b = Business(source="osm", source_id="osm:node/2002", name="Metro Dental Clinic", city="Lahore")
    db_session.add(b)
    db_session.commit()

    lead = SavedLead(
        business_id=b.id,
        status="New",
        priority="High Priority",
        offered_service="Appointment Booking & WhatsApp Bot",
        notes="First discovery batch",
    )
    db_session.add(lead)
    db_session.commit()

    task = FollowUpTask(
        saved_lead_id=lead.id,
        title="Call clinic reception",
        due_date=date.today(),
        priority="High",
    )
    db_session.add(task)
    db_session.commit()

    assert len(lead.tasks) == 1
    assert lead.tasks[0].title == "Call clinic reception"

    # Custom List
    lead_list = LeadList(name="Lahore Clinics")
    db_session.add(lead_list)
    db_session.commit()

    list_item = LeadListItem(list_id=lead_list.id, saved_lead_id=lead.id)
    db_session.add(list_item)
    db_session.commit()

    assert len(lead_list.items) == 1
    assert lead_list.items[0].saved_lead.business.name == "Metro Dental Clinic"

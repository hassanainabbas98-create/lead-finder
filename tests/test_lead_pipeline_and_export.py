"""Automated tests for Phase 5: Lead Pipeline, Custom Lists, Follow-up Tasks, and Filtered CSV Exports."""

import csv
import io
from datetime import date
from app.models.business import Business
from app.models.lead import SavedLead, LeadList, LeadListItem
from app.models.task import FollowUpTask
from app.models.audit import WebsiteAudit


def test_batch_save_leads(client, db_session):
    """Test saving multiple businesses to pipeline in one batch action."""
    b1 = Business(source="osm", source_id="osm:node/5001", name="Alpha Barber", city="Lahore", country="Pakistan")
    b2 = Business(source="osm", source_id="osm:node/5002", name="Beta Salon", city="Lahore", country="Pakistan")
    b3 = Business(source="osm", source_id="osm:node/5003", name="Gamma Cuts", city="Lahore", country="Pakistan")
    db_session.add_all([b1, b2, b3])
    db_session.commit()

    # Create a list
    lst = LeadList(name="Lahore Salons Campaign", color="#10b981")
    db_session.add(lst)
    db_session.commit()

    # Batch save b1 and b2 into lst
    payload = {
        "business_ids": [b1.id, b2.id],
        "status": "New",
        "priority": "High Priority",
        "list_id": lst.id,
    }
    res = client.post("/api/leads/batch-save", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["saved_count"] == 2
    assert data["total_submitted"] == 2

    # Verify both leads are in db
    leads = db_session.query(SavedLead).all()
    lead_biz_ids = [l.business_id for l in leads]
    assert b1.id in lead_biz_ids
    assert b2.id in lead_biz_ids
    assert b3.id not in lead_biz_ids

    # Verify list items
    items = db_session.query(LeadListItem).filter(LeadListItem.list_id == lst.id).all()
    assert len(items) == 2


def test_lead_update_with_contact_dates(client, db_session):
    """Test updating lead with last_contact_date and next_follow_up_date."""
    b = Business(source="osm", source_id="osm:node/5010", name="Apex Clinic", city="Islamabad", country="Pakistan")
    db_session.add(b)
    db_session.commit()

    payload = {
        "business_id": b.id,
        "status": "Contacted",
        "priority": "High Priority",
        "last_contact_date": "2026-10-15",
        "next_follow_up_date": "2026-10-22",
        "offered_service": "AI Voice Receptionist",
        "notes": "Spoke to office manager, interested in demo next week.",
    }
    res = client.post("/api/leads/save", json=payload)
    assert res.status_code == 200
    assert res.json()["success"] is True

    lead = db_session.query(SavedLead).filter(SavedLead.business_id == b.id).first()
    assert lead is not None
    assert lead.status == "Contacted"
    assert lead.priority == "High Priority"
    assert str(lead.last_contact_date) == "2026-10-15"
    assert str(lead.next_follow_up_date) == "2026-10-22"
    assert lead.offered_service == "AI Voice Receptionist"
    assert "office manager" in lead.notes


def test_custom_list_add_and_remove(client, db_session):
    """Test associating and removing a lead from a custom campaign list."""
    b = Business(source="osm", source_id="osm:node/5020", name="Highland Hotel", city="Murree")
    db_session.add(b)
    db_session.commit()

    lead = SavedLead(business_id=b.id, status="New", priority="Medium Priority")
    lst = LeadList(name="Northern Resorts", color="#3b82f6")
    db_session.add_all([lead, lst])
    db_session.commit()

    # Add to list
    res_add = client.post(f"/api/leads/{lead.id}/add-to-list", json={"list_id": lst.id})
    assert res_add.status_code == 200
    assert res_add.json()["success"] is True

    item = db_session.query(LeadListItem).filter(
        LeadListItem.saved_lead_id == lead.id,
        LeadListItem.list_id == lst.id
    ).first()
    assert item is not None

    # Remove from list
    res_rem = client.post(f"/api/leads/{lead.id}/remove-from-list", json={"list_id": lst.id})
    assert res_rem.status_code == 200
    assert res_rem.json()["success"] is True

    item_after = db_session.query(LeadListItem).filter(
        LeadListItem.saved_lead_id == lead.id,
        LeadListItem.list_id == lst.id
    ).first()
    assert item_after is None


def test_list_deletion_cascade(client, db_session):
    """Test deleting a list removes the list and its mappings but leaves saved leads intact."""
    b = Business(source="osm", source_id="osm:node/5030", name="Capital Cafe", city="Islamabad")
    db_session.add(b)
    db_session.commit()

    lead = SavedLead(business_id=b.id, status="New")
    lst = LeadList(name="Temporary Test List")
    db_session.add_all([lead, lst])
    db_session.commit()

    item = LeadListItem(saved_lead_id=lead.id, list_id=lst.id)
    db_session.add(item)
    db_session.commit()

    # Delete list via API
    res_del = client.delete(f"/api/lists/{lst.id}")
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True

    # List deleted
    assert db_session.query(LeadList).filter(LeadList.id == lst.id).first() is None
    # List item deleted
    assert db_session.query(LeadListItem).filter(LeadListItem.list_id == lst.id).first() is None
    # SavedLead still exists!
    assert db_session.query(SavedLead).filter(SavedLead.id == lead.id).first() is not None


def test_create_task_and_toggle(client, db_session):
    """Test creating a follow-up task via JSON API, toggling completed state, and deleting."""
    b = Business(source="osm", source_id="osm:node/5040", name="Prime Dental", city="Peshawar")
    db_session.add(b)
    db_session.commit()

    lead = SavedLead(business_id=b.id, status="Interested")
    db_session.add(lead)
    db_session.commit()

    # Create task
    task_payload = {
        "saved_lead_id": lead.id,
        "title": "Send proposal for online booking module",
        "due_date": "2026-10-25",
        "priority": "High",
        "description": "Include standard retainer pricing",
    }
    res_task = client.post("/api/tasks", json=task_payload)
    assert res_task.status_code == 200
    data = res_task.json()
    assert data["success"] is True
    task_id = data["task_id"]

    task = db_session.query(FollowUpTask).filter(FollowUpTask.id == task_id).first()
    assert task is not None
    assert task.title == "Send proposal for online booking module"
    assert task.is_completed is False

    # Toggle task to completed
    res_toggle = client.post(f"/api/tasks/{task_id}/toggle", json={"is_completed": True})
    assert res_toggle.status_code == 200
    assert res_toggle.json()["is_completed"] is True

    db_session.refresh(task)
    assert task.is_completed is True
    assert task.completed_at is not None

    # Delete task
    res_del = client.delete(f"/api/tasks/{task_id}")
    assert res_del.status_code == 200
    assert db_session.query(FollowUpTask).filter(FollowUpTask.id == task_id).first() is None


def test_filtered_leads_export_csv(client, db_session):
    """Test exporting leads with status and priority filters and verifying CSV content."""
    b1 = Business(source="osm", source_id="osm:node/6001", name="Elite Fitness", city="Lahore")
    b2 = Business(source="osm", source_id="osm:node/6002", name="Metro Auto", city="Karachi")
    db_session.add_all([b1, b2])
    db_session.commit()

    audit1 = WebsiteAudit(
        business_id=b1.id,
        url_checked="https://elitefitness.example.com",
        status="Completed",
        has_chatbot="Detected",
        has_online_booking="Not Detected",
    )
    db_session.add(audit1)

    lead1 = SavedLead(business_id=b1.id, status="Interested", priority="High Priority", opportunity_score=85)
    lead2 = SavedLead(business_id=b2.id, status="New", priority="Low Priority", opportunity_score=30)
    db_session.add_all([lead1, lead2])
    db_session.commit()

    # Export High Priority only
    res_high = client.get("/api/export/leads?priority=High+Priority")
    assert res_high.status_code == 200
    assert res_high.headers["content-type"].startswith("text/csv")
    csv_text = res_high.text

    reader = list(csv.reader(io.StringIO(csv_text)))
    headers = reader[0]
    assert "Business Name" in headers
    assert "Chatbot Status" in headers
    assert "Booking Status" in headers
    assert "Opportunity Score" in headers

    # Verify row contents
    data_rows = reader[1:]
    assert len(data_rows) == 1
    assert data_rows[0][0] == "Elite Fitness"
    # Chatbot Status column
    chatbot_idx = headers.index("Chatbot Status")
    booking_idx = headers.index("Booking Status")
    assert data_rows[0][chatbot_idx] == "Detected"
    assert data_rows[0][booking_idx] == "Not Detected"


def test_selected_businesses_and_leads_export(client, db_session):
    """Test exporting specific selections of businesses and leads via POST."""
    b1 = Business(source="osm", source_id="osm:node/7001", name="Selected Studio", city="Lahore")
    b2 = Business(source="osm", source_id="osm:node/7002", name="Unselected Cafe", city="Lahore")
    db_session.add_all([b1, b2])
    db_session.commit()

    lead1 = SavedLead(business_id=b1.id, status="New")
    db_session.add(lead1)
    db_session.commit()

    # Export selected business
    res_b = client.post("/api/export/selected-businesses", json={"business_ids": [b1.id]})
    assert res_b.status_code == 200
    assert "Selected Studio" in res_b.text
    assert "Unselected Cafe" not in res_b.text

    # Export selected lead
    res_l = client.post("/api/export/selected-leads", json={"lead_ids": [lead1.id]})
    assert res_l.status_code == 200
    assert "Selected Studio" in res_l.text


def test_csv_formula_injection_guard(client, db_session):
    """Verify spreadsheet formula injection is mitigated in exported CSV."""
    malicious_name = "=SUM(1+1)"
    b = Business(source="osm", source_id="osm:node/8001", name=malicious_name, city="Lahore")
    db_session.add(b)
    db_session.commit()

    lead = SavedLead(business_id=b.id, status="New", notes="@HYPERLINK('http://evil.com')")
    db_session.add(lead)
    db_session.commit()

    res = client.get("/api/export/leads")
    assert res.status_code == 200
    # Values starting with = or @ should be prefixed with single quote '
    assert "'=SUM(1+1)" in res.text
    assert "'@HYPERLINK" in res.text


def test_lead_manual_email_update(client, db_session):
    """Test updating lead email and Gmail ID directly via API."""
    b = Business(source="osm", source_id="osm:node/8501", name="Alpha Barber", city="Lahore")
    db_session.add(b)
    db_session.commit()

    lead = SavedLead(business_id=b.id, status="New")
    db_session.add(lead)
    db_session.commit()

    # Update with a Gmail ID
    payload = {
        "business_id": b.id,
        "email": "alphabarber.lahore@gmail.com",
        "phone": "+92 300 9876543",
    }
    res = client.post("/api/leads/save", json=payload)
    assert res.status_code == 200
    assert res.json()["success"] is True

    db_session.refresh(b)
    assert b.email == "alphabarber.lahore@gmail.com"
    assert b.phone == "+92 300 9876543"


def test_overpass_gmail_extraction():
    """Test extracting email and Gmail IDs from raw OSM tags."""
    from app.services.discovery.overpass import OverpassDiscoveryProvider
    provider = OverpassDiscoveryProvider()

    elements = [
        {
            "type": "node",
            "id": 101,
            "tags": {
                "name": "Barber A",
                "operator:email": "contact.barbera@gmail.com",
                "phone": "+92 42 1234567",
            }
        },
        {
            "type": "node",
            "id": 102,
            "tags": {
                "name": "Clinic B",
                "description": "For bookings, reach out to clinicb.official@gmail.com anytime.",
            }
        }
    ]

    records = provider._normalize_elements(
        elements=elements,
        category="Barber",
        city="Lahore",
        country="Pakistan",
        max_results=10,
    )
    assert len(records) == 2
    assert records[0].email == "contact.barbera@gmail.com"
    assert records[1].email == "clinicb.official@gmail.com"


def test_search_contact_filter_gmail(client, db_session):
    """Test filtering businesses by contact_filter=has_gmail."""
    b1 = Business(source="osm", source_id="osm:node/9901", name="Gmail Cafe", city="Lahore", country="Pakistan", category="cafe", email="cafe@gmail.com")
    b2 = Business(source="osm", source_id="osm:node/9902", name="No Email Cafe", city="Lahore", country="Pakistan", category="cafe")
    db_session.add_all([b1, b2])
    db_session.commit()

    res = client.get("/search?category=cafe&city=Lahore&country=Pakistan&discover=0&contact_filter=has_gmail")
    assert res.status_code == 200
    assert "Gmail Cafe" in res.text
    assert "No Email Cafe" not in res.text


def test_update_lead_status_kanban(client, db_session):
    """Test updating lead status via the Kanban drag-and-drop endpoint."""
    b = Business(source="osm", source_id="osm:node/8801", name="Kanban Test Salon", city="Lahore", country="Pakistan")
    db_session.add(b)
    db_session.commit()

    lead = SavedLead(business_id=b.id, status="New", priority="High Priority")
    db_session.add(lead)
    db_session.commit()

    res = client.post(f"/api/leads/{lead.id}/status", json={"status": "Interested"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["status"] == "Interested"

    db_session.refresh(lead)
    assert lead.status == "Interested"


def test_webhook_settings_and_dispatch(client, db_session):
    """Test saving webhook setting and dispatching businesses to webhook endpoint."""
    # Step 1: Save webhook URL setting (TestClient follows 303 to 200)
    res_set = client.post("/api/settings/webhook", data={"webhook_url": "https://httpbin.org/post"}, follow_redirects=False)
    assert res_set.status_code == 303


    # Step 2: Create business and lead
    b = Business(source="osm", source_id="osm:node/8802", name="Webhook Prospect", city="Peshawar", country="Pakistan", phone="+92 300 1234567")
    db_session.add(b)
    db_session.commit()

    # Step 3: Dispatch with custom dummy webhook or mock
    res_dispatch = client.post("/api/webhook/dispatch", json={
        "business_ids": [b.id],
        "custom_webhook_url": "https://httpbin.org/post",
        "source": "test_suite"
    })
    assert res_dispatch.status_code == 200
    data = res_dispatch.json()
    assert data["dispatched_count"] == 1
    assert data["webhook_url"] == "https://httpbin.org/post"


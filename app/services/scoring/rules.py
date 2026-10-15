"""Scoring rules and configurable weights for business opportunity prioritization."""

# Point allocations for observable digital presence signals
SCORE_WEIGHTS = {
    # Website presence signals
    "no_website_listed": 35,          # Prime prospect for new website development
    "website_inaccessible": 25,       # Prospect for website recovery / redesign
    "has_website": 5,                 # Base presence; opportunity for enhancement

    # Digital feature signals (only evaluated when website is found & audited)
    "no_booking_detected": 15,        # Opportunity for online appointment scheduling
    "no_chatbot_detected": 15,        # Opportunity for AI customer service / WhatsApp bot
    "no_ordering_detected": 10,       # Opportunity for direct food/product ordering (restaurants/retail)
    "not_mobile_friendly": 10,        # Opportunity for mobile-responsive redesign
    "no_https": 10,                   # Opportunity for security hardening & SSL

    # Outreach & contact signals (makes prospect immediately actionable)
    "has_phone": 15,                  # Can be called directly or pitched voice agent
    "has_whatsapp": 10,               # Can receive automated WhatsApp demo
    "has_email": 10,                  # Direct email outreach channel

    # Target industry alignment
    "target_industry_match": 10,      # Barber, clinic, restaurant, hotel, school, real estate
}

HIGH_OPPORTUNITY_CATEGORIES = {
    "barber", "hairdresser", "salon", "clinic", "doctor", "dentist",
    "restaurant", "cafe", "hotel", "school", "college", "real estate",
    "gym", "fitness", "bakery", "car repair",
}


def get_priority_tier(score: int) -> str:
    """Map numeric score (0-100) to priority category."""
    if score >= 70:
        return "High Priority"
    elif score >= 50:
        return "Medium Priority"
    elif score >= 30:
        return "Low Priority"
    return "Needs Review"

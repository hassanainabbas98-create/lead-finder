from typing import List, Tuple, Dict, Any, Set

# Standard mappings from common user category keywords to OSM key-value filter lists
CATEGORY_TAG_MAP: Dict[str, Dict[str, Any]] = {
    "barber": {
        "display_name": "Barber Shop / Hairdresser",
        "aliases": ["barber", "barbers", "barber shop", "barbershop", "hairdresser", "hairdressers", "hair salon", "haircut"],
        "tags": ['["shop"="hairdresser"]', '["amenity"="barber"]'],
        "default_service": "Website Development & Appointment Booking",
    },
    "hairdresser": {
        "display_name": "Hairdresser / Salon",
        "aliases": ["hairdresser", "hairdressers", "hair salon", "hair", "salon", "salons", "beauty parlour"],
        "tags": ['["shop"="hairdresser"]', '["shop"="beauty"]'],
        "default_service": "Salon Website & Online Appointment Booking",
    },
    "salon": {
        "display_name": "Beauty Salon",
        "aliases": ["salon", "salons", "beauty salon", "spa", "parlour", "parlor", "makeover"],
        "tags": ['["shop"="beauty"]', '["shop"="hairdresser"]'],
        "default_service": "Salon Website & Online Booking System",
    },
    "clinic": {
        "display_name": "Medical Clinic",
        "aliases": ["clinic", "clinics", "medical clinic", "dispensary", "health center", "medical center"],
        "tags": ['["amenity"="clinic"]', '["amenity"="doctors"]', '["healthcare"="clinic"]', '["healthcare"="doctor"]'],
        "default_service": "Clinic Website & Patient Appointment System",
    },
    "doctor": {
        "display_name": "Doctor / Medical Practice",
        "aliases": ["doctor", "doctors", "physician", "physicians", "specialist", "medical practice"],
        "tags": ['["amenity"="doctors"]', '["healthcare"="doctor"]', '["amenity"="clinic"]'],
        "default_service": "Doctor Profile Website & Online Scheduling",
    },
    "hospital": {
        "display_name": "Hospital",
        "aliases": ["hospital", "hospitals", "medical center", "healthcare"],
        "tags": ['["amenity"="hospital"]', '["healthcare"="hospital"]'],
        "default_service": "Hospital Portal & Inquiry Chatbot",
    },
    "dentist": {
        "display_name": "Dental Clinic",
        "aliases": ["dentist", "dentists", "dental", "dental clinic", "orthodontist"],
        "tags": ['["amenity"="dentist"]', '["healthcare"="dentist"]'],
        "default_service": "Dental Website & Appointment Booking",
    },
    "restaurant": {
        "display_name": "Restaurant",
        "aliases": ["restaurant", "restaurants", "dining", "eatery", "fast food", "diner"],
        "tags": ['["amenity"="restaurant"]', '["amenity"="fast_food"]'],
        "default_service": "Restaurant Website & Online Ordering System",
    },
    "cafe": {
        "display_name": "Cafe / Coffee Shop",
        "aliases": ["cafe", "cafes", "coffee", "coffee shop", "tea shop", "cafeteria"],
        "tags": ['["amenity"="cafe"]'],
        "default_service": "Cafe Website & Digital QR Menu",
    },
    "bakery": {
        "display_name": "Bakery",
        "aliases": ["bakery", "bakeries", "bakehouse", "pastry", "pastries", "confectionery"],
        "tags": ['["shop"="bakery"]'],
        "default_service": "Bakery Website & Online Pre-orders",
    },
    "hotel": {
        "display_name": "Hotel / Lodging",
        "aliases": ["hotel", "hotels", "motel", "motels", "resort", "resorts", "guest house", "guesthouse", "lodging", "hostel"],
        "tags": ['["tourism"="hotel"]', '["tourism"="motel"]', '["tourism"="guest_house"]'],
        "default_service": "Hotel Booking Website & Guest Inquiry Chatbot",
    },
    "school": {
        "display_name": "School / Academy",
        "aliases": ["school", "schools", "academy", "academies", "college", "colleges", "kindergarten", "education", "high school", "grammar school", "institute"],
        "tags": ['["amenity"="school"]', '["amenity"="college"]', '["amenity"="kindergarten"]'],
        "default_service": "School Portal, CMS & Admissions Chatbot",
    },
    "college": {
        "display_name": "College / University",
        "aliases": ["college", "colleges", "university", "universities", "institute", "campus"],
        "tags": ['["amenity"="college"]', '["amenity"="university"]'],
        "default_service": "College CMS & Admissions Assistant",
    },
    "real estate": {
        "display_name": "Real Estate Agency",
        "aliases": ["real estate", "real estate agency", "realtor", "property", "estate agent", "properties"],
        "tags": ['["office"="estate_agent"]'],
        "default_service": "Property Listings Website & Lead Capture Chatbot",
    },
    "gym": {
        "display_name": "Gym / Fitness Center",
        "aliases": ["gym", "gyms", "fitness", "fitness center", "fitness centre", "workout", "sports center"],
        "tags": ['["leisure"="fitness_centre"]', '["leisure"="sports_centre"]'],
        "default_service": "Gym Membership Portal & Class Booking System",
    },
    "pharmacy": {
        "display_name": "Pharmacy",
        "aliases": ["pharmacy", "pharmacies", "chemist", "chemists", "drugstore", "drugstores", "medical store"],
        "tags": ['["amenity"="pharmacy"]', '["healthcare"="pharmacy"]'],
        "default_service": "Pharmacy Catalog Website & Prescription Upload",
    },
    "car repair": {
        "display_name": "Auto Repair / Mechanic",
        "aliases": ["car repair", "auto repair", "mechanic", "mechanics", "auto service", "garage", "workshop"],
        "tags": ['["shop"="car_repair"]'],
        "default_service": "Auto Shop Website & Service Booking System",
    },
}


def stem_category_word(word: str) -> str:
    """Helper to convert plural words into root singular stems."""
    w = word.strip().lower()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("es") and len(w) > 3:
        return w[:-2]
    if w.endswith("s") and len(w) > 3:
        return w[:-1]
    return w


def resolve_osm_tags(category_query: str) -> Tuple[List[str], bool, str, str]:
    """
    Resolve user query to structured OSM tags or fallback keyword query.
    Handles singular, plural, and category alias variations.

    Returns:
        (osm_tags_list, is_structured_match, friendly_category_name, default_service)
    """
    cleaned = category_query.strip().lower()
    stem = stem_category_word(cleaned)

    # 1. Exact match on main key or aliases
    for key, data in CATEGORY_TAG_MAP.items():
        aliases = [a.lower() for a in data.get("aliases", [key])]
        if key == cleaned or key == stem or cleaned in aliases or stem in aliases:
            return (
                data["tags"],
                True,
                data["display_name"],
                data["default_service"],
            )

    # 2. Substring or word match across aliases
    for key, data in CATEGORY_TAG_MAP.items():
        aliases = [a.lower() for a in data.get("aliases", [key])]
        if any(a in cleaned or cleaned in a or a in stem or stem in a for a in aliases):
            return (
                data["tags"],
                True,
                data["display_name"],
                data["default_service"],
            )

    # 2. Substring match on main dictionary keys
    for key, data in CATEGORY_TAG_MAP.items():
        if key in cleaned or cleaned in key or key in stem or stem in key:
            return (
                data["tags"],
                True,
                data["display_name"],
                data["default_service"],
            )

    # 3. Fallback keyword search across common commercial tags
    fallback_tags = [
        f'["name"~"{cleaned}",i]["shop"]',
        f'["name"~"{cleaned}",i]["amenity"]',
        f'["name"~"{cleaned}",i]["office"]',
    ]
    return (fallback_tags, False, category_query.title(), "Website Development & Digital Automation")


def get_category_search_variants(category_query: str) -> List[str]:
    """
    Generate search variants for a category query to ensure singular/plural
    and display name matches in database queries.

    For example, 'schools' will yield:
    ['schools', 'school', 'School / Academy', 'School', 'Academy']
    """
    if not category_query:
        return []

    cleaned = category_query.strip().lower()
    variants: Set[str] = {cleaned, category_query.strip()}

    # Add singular stem
    stem = stem_category_word(cleaned)
    variants.add(stem)

    # If it ends in singular, also add common plural
    if not cleaned.endswith("s"):
        variants.add(cleaned + "s")
        if cleaned.endswith("y") and len(cleaned) > 2:
            variants.add(cleaned[:-1] + "ies")

    # Match against CATEGORY_TAG_MAP to add display_name and category aliases
    for key, data in CATEGORY_TAG_MAP.items():
        aliases = data.get("aliases", [key])
        if (
            key in cleaned
            or cleaned in key
            or key in stem
            or stem in key
            or any(a in cleaned or cleaned in a or a in stem for a in aliases)
        ):
            display_name = data["display_name"]
            variants.add(display_name)
            variants.add(key)
            # Add individual tokens from display name (e.g. "School", "Academy" from "School / Academy")
            for token in display_name.replace("/", " ").split():
                clean_tok = token.strip()
                if len(clean_tok) > 2:
                    variants.add(clean_tok)
            # Add first few primary aliases
            for a in aliases[:4]:
                variants.add(a)

    return [v for v in variants if v]


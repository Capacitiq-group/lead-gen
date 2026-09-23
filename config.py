"""
Configuration for the Capacitiq lead generation script.
Edit this file to adjust categories, cities, targets, and filter rules.
"""

# ---------------------------------------------------------------------------
# TARGETS
# ---------------------------------------------------------------------------
BUSINESS_TARGET = 1000
PARTNER_TARGET = 500

# ---------------------------------------------------------------------------
# BUSINESS CATEGORIES (what you're selling TO)
# ---------------------------------------------------------------------------
BUSINESS_CATEGORIES = {
    "Professional Services": [
        "law firm", "accounting firm", "recruitment agency", "consulting firm",
        "financial services company", "insurance broker", "property agency",
        "training provider",
    ],
    "Health & Beauty": [
        "hair salon", "barbershop", "nail studio", "spa", "aesthetic clinic",
        "wellness centre", "fitness studio",
    ],
    "Home & Local Services": [
        "plumber", "electrician", "cleaning company", "security company",
        "appliance repair service", "construction company", "landscaping company",
        "auto repair shop",
    ],
    "Retail & E-commerce": [
        "clothing store", "furniture store", "electronics retailer",
        "online store", "specialty retailer", "bakery",
    ],
    "Hospitality & Events": [
        "restaurant", "catering company", "event venue", "wedding business",
        "photographer", "event planner", "travel agency", "guest house",
    ],
    "Education": [
        "tutoring service", "driving school", "training centre",
        "educational institution", "life coach",
    ],
    "Creative & Digital": [
        "marketing agency", "design studio", "web developer",
        "photography studio", "media company", "creative agency",
    ],
}

# ---------------------------------------------------------------------------
# PARTNER CATEGORIES (who you're partnering WITH)
# ---------------------------------------------------------------------------
PARTNER_CATEGORIES = {
    "Web & Design": [
        "website developer", "freelance web designer", "web development studio",
        "branding studio", "graphic design agency",
    ],
    "Marketing & Growth": [
        "SEO agency", "digital marketing agency", "e-commerce developer",
    ],
    "IT & Consulting": [
        "IT services provider", "business consultant",
    ],
}

# ---------------------------------------------------------------------------
# SOUTH AFRICAN CITIES/REGIONS TO ROTATE THROUGH
# (keeps search queries from all returning the same top results)
# ---------------------------------------------------------------------------
SA_CITIES = [
    "Johannesburg", "Cape Town", "Durban", "Pretoria", "Port Elizabeth",
    "Bloemfontein", "East London", "Polokwane", "Nelspruit", "Centurion",
    "Sandton", "Stellenbosch", "George", "Pietermaritzburg", "Kimberley",
    "South Africa",  # generic fallback, no city qualifier
]

# ---------------------------------------------------------------------------
# CHAT WIDGET SIGNATURES — if any of these strings appear in a page's raw
# HTML/JS, the site is treated as having a live chat widget and excluded.
# ---------------------------------------------------------------------------
CHAT_WIDGET_SIGNATURES = [
    "widget.intercom.io", "intercomcdn.com",
    "js.driftt.com", "drift.com/embed",
    "embed.tawk.to",
    "static.zdassets.com", "zendesk chat", "zopim.com",
    "client.crisp.chat",
    "widget.freshworks.com", "freshchat",
    "livechatinc.com",
    "widget.tidiochat.com", "code.tidio.co",
    "chatra.io",
    "gorgias.chat",
    "hubspot chat", "js.hs-scripts.com/conversation",
    "purechat.com",
    "smartsupp.com",
    "olark.com",
    "userlike.com",
    "whatsapp-widget", "wa-chat-widget",  # generic floating WA chat widgets
]

# ---------------------------------------------------------------------------
# REQUEST / CRAWL SETTINGS
# ---------------------------------------------------------------------------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 12          # seconds
MIN_DELAY_SECONDS = 2.0       # minimum pause between outbound requests
MAX_DELAY_SECONDS = 5.0       # maximum pause between outbound requests
SEARCH_RESULTS_PER_QUERY = 10 # how many DuckDuckGo results to take per query
MAX_RETRIES = 2

# Output / state files
OUTPUT_XLSX = "capacitiq_leads.xlsx"
STATE_FILE = "leadgen_state.json"
LOG_FILE = "leadgen_log.txt"

"""
Capacitiq Lead Generation Script
=================================

Finds South African businesses (and separately, web/marketing/IT partners)
that have a live website, no chat widget, and a public email address —
using only free, public sources (no API keys required).

USAGE
-----
    python main.py                  # run until both targets are hit
    python main.py --max-queries 50 # cap this run to N search queries
    python main.py --reset          # wipe saved progress and start over

The script saves progress as it goes (leadgen_state.json) so it can be
stopped (Ctrl+C) and resumed later without losing work or re-crawling
sites it has already checked.

OUTPUT
------
    capacitiq_leads.xlsx  — two tabs: "Businesses" and "Partners"
    leadgen_log.txt       — a running log of what happened on each run

REALISTIC EXPECTATIONS
-----------------------
This relies on DuckDuckGo's public HTML search page rather than a paid
search API, out of respect for the "no API keys" constraint. That means:
  - It's slow by design (polite delays between every request) — expect
    roughly 1 site every 3-7 seconds, so 1500 accepted leads is a multi-hour
    to multi-day run, not a five-minute one.
  - Not every query will yield results that pass the filters (many SA
    small businesses don't have email visible on their homepage, or don't
    have a website at all) — so the script will process more candidate
    sites than it accepts.
  - DuckDuckGo may rate-limit or CAPTCHA-block the crawler if run too
    aggressively. If a run starts returning zero candidates, wait a while
    before trying again, or swap in a paid search API (Google Custom
    Search / SerpAPI) in scraper.find_candidate_urls — the rest of the
    pipeline (crawl/filter/output) will work unchanged.
"""

import argparse
import itertools
import json
import os
import sys
from datetime import datetime

import pandas as pd

import config
import scraper


def log(message: str):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line)
    with open(config.LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state():
    if os.path.exists(config.STATE_FILE):
        with open(config.STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "completed_queries": [],   # queries already searched this run/prior runs
        "seen_urls": [],           # candidate URLs already crawled (any outcome)
        "business_rows": [],       # accepted business leads
        "partner_rows": [],        # accepted partner leads
    }


def save_state(state):
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def build_query_list(categories: dict, cities: list) -> list:
    """Build (category_group, search_term, city, full_query) tuples,
    rotating cities so results aren't dominated by one area."""
    queries = []
    city_cycle = itertools.cycle(cities)
    for group, terms in categories.items():
        for term in terms:
            city = next(city_cycle)
            if city == "South Africa":
                full_query = f"{term} South Africa"
            else:
                full_query = f"{term} in {city}, South Africa"
            queries.append((group, term, city, full_query))
    return queries


def result_to_row(result: scraper.SiteResult) -> dict:
    return {
        "Business Name": result.business_name,
        "Category": result.category,
        "Website": result.website,
        "Has Contact Form": "Y" if result.has_contact_form else "N",
        "Email": result.email or "",
        "Phone": result.phone or "",
        "WhatsApp": f"https://wa.me/{result.whatsapp}" if result.whatsapp else "",
        "LinkedIn": result.linkedin or "",
        "Other Socials": "; ".join(result.other_socials) if result.other_socials else "",
        "Contact Person": result.contact_person or "",
        "Source Query": result.source_query,
    }


OUTPUT_COLUMNS = [
    "Business Name", "Category", "Website", "Has Contact Form", "Email",
    "Phone", "WhatsApp", "LinkedIn", "Other Socials", "Contact Person",
    "Source Query",
]


def write_output(state):
    biz_df = pd.DataFrame(state["business_rows"], columns=OUTPUT_COLUMNS)
    partner_df = pd.DataFrame(state["partner_rows"], columns=OUTPUT_COLUMNS)
    with pd.ExcelWriter(config.OUTPUT_XLSX, engine="openpyxl") as writer:
        biz_df.to_excel(writer, sheet_name="Businesses", index=False)
        partner_df.to_excel(writer, sheet_name="Partners", index=False)
    log(f"Wrote output: {len(biz_df)} businesses, {len(partner_df)} partners -> {config.OUTPUT_XLSX}")


def run(max_queries=None):
    state = load_state()
    seen_urls = set(state["seen_urls"])
    completed_queries = set(state["completed_queries"])

    business_queries = build_query_list(config.BUSINESS_CATEGORIES, config.SA_CITIES)
    partner_queries = build_query_list(config.PARTNER_CATEGORIES, config.SA_CITIES)

    # Interleave so a run makes progress on both buckets rather than
    # exhausting one before starting the other.
    all_queries = [("business", q) for q in business_queries] + \
                  [("partner", q) for q in partner_queries]

    queries_run_this_session = 0

    for bucket, (group, term, city, full_query) in all_queries:
        target = config.BUSINESS_TARGET if bucket == "business" else config.PARTNER_TARGET
        row_list_key = "business_rows" if bucket == "business" else "partner_rows"

        if len(state[row_list_key]) >= target:
            continue  # this bucket is already full
        if full_query in completed_queries:
            continue  # already searched this exact query in a prior run
        if max_queries is not None and queries_run_this_session >= max_queries:
            log(f"Reached --max-queries limit ({max_queries}) for this session. Stopping.")
            break

        log(f"[{bucket}] Searching: {full_query}")
        try:
            candidate_urls = scraper.find_candidate_urls(full_query)
        except Exception as e:
            log(f"  search failed: {e}")
            candidate_urls = []

        completed_queries.add(full_query)
        queries_run_this_session += 1

        for url in candidate_urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                result = scraper.analyze_website(group, url, full_query)
            except Exception as e:
                log(f"  crawl failed for {url}: {e}")
                continue

            if result.passes_filters():
                row = result_to_row(result)
                state[row_list_key].append(row)
                log(f"  ACCEPTED [{bucket}] {result.business_name} — {url}")
            else:
                reason = []
                if not result.reachable:
                    reason.append("unreachable")
                if result.has_chat_widget:
                    reason.append("has chat widget")
                if result.reachable and not result.email:
                    reason.append("no email found")
                log(f"  skipped {url} ({', '.join(reason) or 'failed filters'})")

            if len(state[row_list_key]) >= target:
                log(f"[{bucket}] Target of {target} reached.")
                break

        # Persist progress after every query, not just at the end —
        # protects against interruptions mid-run.
        state["seen_urls"] = list(seen_urls)
        state["completed_queries"] = list(completed_queries)
        save_state(state)
        write_output(state)

        if len(state["business_rows"]) >= config.BUSINESS_TARGET and \
           len(state["partner_rows"]) >= config.PARTNER_TARGET:
            log("Both targets reached. Done.")
            break

    write_output(state)
    log(
        f"Session complete. Totals so far: "
        f"{len(state['business_rows'])}/{config.BUSINESS_TARGET} businesses, "
        f"{len(state['partner_rows'])}/{config.PARTNER_TARGET} partners."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capacitiq lead generation")
    parser.add_argument("--max-queries", type=int, default=None,
                         help="Cap the number of search queries run this session")
    parser.add_argument("--reset", action="store_true",
                         help="Delete saved progress and start fresh")
    args = parser.parse_args()

    if args.reset:
        for f in (config.STATE_FILE, config.LOG_FILE, config.OUTPUT_XLSX):
            if os.path.exists(f):
                os.remove(f)
        log("Progress reset.")

    run(max_queries=args.max_queries)

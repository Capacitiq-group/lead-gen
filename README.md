# Capacitiq Lead Generation Script

Finds South African businesses (for the 1000-lead list) and web/marketing/IT
partners (for the 500-lead list) that:

- have a **live, reachable website**
- do **not** have a chat widget on it (Intercom, Drift, Tawk.to, Zendesk,
  Crisp, etc.)
- have a **public email address** somewhere on the site

...and pulls whatever else is publicly available: phone number, WhatsApp
link, LinkedIn, other social handles, and — where it can be confidently
guessed — a contact person's name.

No API keys required. It finds candidate websites using DuckDuckGo's public
search page rather than a paid search API.

## 1. Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Run it

```bash
python main.py
```

That's it — it'll keep going until it hits 1000 business leads and 500
partner leads, or you stop it. Progress is saved continuously, so:

- **Stop it any time** with Ctrl+C — nothing is lost.
- **Resume** by just running `python main.py` again — it picks up where it
  left off and skips queries/sites it's already checked.
- **Start over** with `python main.py --reset` if you want a clean slate.
- **Cap a session** with `python main.py --max-queries 30` if you want to
  run it in short bursts (e.g. to avoid DuckDuckGo rate-limiting) rather
  than one long unattended run.

## 3. Output

- `capacitiq_leads.xlsx` — two tabs, **Businesses** and **Partners**, each
  with: Business Name, Category, Website, Has Contact Form, Email, Phone,
  WhatsApp, LinkedIn, Other Socials, Contact Person, Source Query.
- `leadgen_log.txt` — a plain-text log of every site checked and why it was
  accepted or skipped, useful for sanity-checking the filter is doing what
  you expect.
- `leadgen_state.json` — internal progress file (queries done, URLs seen,
  accepted rows). Delete it (or use `--reset`) to start fresh.

## 4. Realistic expectations — please read this before you judge the yield

This is built on **free public search**, not a paid API, because that's
what you have available right now. That trade-off matters:

- **It's slow on purpose.** Every request has a random 2–5 second delay
  before it, to avoid getting blocked. Expect roughly one site checked
  every 3–7 seconds. Getting to 1500 *accepted* leads (not just checked
  sites) is realistically a run that needs to be left going for hours,
  possibly across more than one sitting — not a five-minute script.
- **Most candidate sites won't pass the filter.** A lot of small SA
  businesses either don't have a website at all, don't show an email
  anywhere on the page (Facebook-only contact, phone-only, etc.), or do
  have a chat widget. Expect the log to show many more "skipped" lines
  than "accepted" ones — that's the filter working correctly, not a bug.
- **DuckDuckGo may rate-limit or CAPTCHA the crawler** if run too hard.
  If a run suddenly returns zero candidates for every query, that's what's
  happening — stop, wait an hour or more, and resume. Running with
  `--max-queries` in smaller bursts across a day is the safest pattern.
- **If/when you do get a search API key** (Google Custom Search, SerpAPI,
  Google Places, or an Apollo export), the fix is contained to one
  function — `find_candidate_urls()` in `scraper.py`. Swap its internals
  to call that API instead of DuckDuckGo, and the rest of the pipeline
  (crawling, filtering, dedup, Excel output) works unchanged. That would
  make this dramatically faster and more reliable at this volume.

## 5. Editing categories/cities/targets

Everything you'd want to tweak lives in `config.py`:
- `BUSINESS_CATEGORIES` / `PARTNER_CATEGORIES` — the search terms per group
- `SA_CITIES` — cities rotated through to spread results geographically
- `BUSINESS_TARGET` / `PARTNER_TARGET` — currently 1000 / 500
- `CHAT_WIDGET_SIGNATURES` — add to this list if you spot a widget the
  script isn't catching
- `MIN_DELAY_SECONDS` / `MAX_DELAY_SECONDS` — increase these if you're
  getting rate-limited; decrease at your own risk

## 6. A note on how this is meant to be used

Everything this script collects is public information already published on
a business's own website (or their public social profiles). It doesn't log
in anywhere, doesn't bypass any access controls, and respects normal
courtesy delays between requests. Worth keeping in mind for GDPR/POPIA
purposes: once you're emailing these contacts, South Africa's POPIA (and
UK/EU GDPR if you ever point this elsewhere) still governs how you use and
store the data — this script only handles the *finding* part.

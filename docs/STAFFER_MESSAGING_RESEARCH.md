# Research: Messaging That Works for Congressional Staffers

Quick reference so our script library and UI help constituents make the **most impact** when calling or emailing—based on Congressional Management Foundation (CMF) surveys and Hill staff guidance.

---

## What Staffers Need to Know (Phone & Email)

| Need | Why |
|------|-----|
| **Name and full address** | Offices verify you're in the member’s district/state. Only constituent contacts are logged and weighed. |
| **Clear ask** | e.g. “Please vote for/against …”, “Please co-sponsor …”, “Support/oppose [bill or issue].” |
| **One issue per contact** | Easier to log, route, and report. Avoid bundling multiple topics in one call/email. |
| **Short message** | Email: ~7–10 sentences. Calls: under ~5 minutes. Concise is more likely to be read and noted. |
| **Optional: bill number** | When there’s a specific bill, including the number helps staff log and route (e.g. “H.R. 1234” or “S. 567”). |

---

## What Staffers Often Ask (Especially on Calls)

- **“Where are you calling from?” / “What’s your address?”** — To confirm you’re a constituent so your position gets counted.
- **“Do you want a written response?”** — Many callers only want their position recorded; saying “No, just record my position” is fine and saves staff time.

So our **call scripts** should prompt the constituent to say their city/district (or state for senators) and to know they can say they don’t need a callback.

---

## What Makes Messages Persuasive (CMF Research)

- **Individualized > form.** Personalized emails/letters are far more influential than form text. Our app helps users personalize (edit script, add their own sentence).
- **Personal story.** A sentence on how the issue affects the constituent or their community is highly valued; staff say local impact is helpful but rarely included.
- **Specific ask.** A measurable request (vote for, co-sponsor, support/oppose X) is more actionable than vague “please look into this.”
- **Polite and brief.** Courteous tone and brevity get better reception than long or hostile messages.

---

## How We Apply This

1. **Script library**
   - Call scripts start with constituent ID: e.g. “I’m a constituent from [city/district or state]” so users are ready when staff ask where they’re from.
   - One clear ask per script; optional “You can just record my position” so users know they don’t have to request a callback.
   - Email bodies: short (2–3 paragraphs), clear ask, polite close. Optional line encouraging users to add one personal sentence.

2. **UI (ScriptFlow)**
   - **Calls:** Short tip that staff may ask for name/address to verify constituency, and that they can say “just record my position” if they don’t need a response.
   - **Email/contact form:** Remind users to fill in name and full address in the form so the office can verify they’re a constituent.

3. **Gemini prompt (backend)**
   - Already asks for “constituent from [state]” in call script; keep encouraging a clear ask and brief, polite tone.

---

## Sources (summary)

- Congressional Management Foundation: *Communicating with Congress*, *Citizen-Centric Advocacy*, “It’s Not How You Send It, It’s What’s Inside” — staff surveys on what influences undecided members (individualized contact, in-person visits, short personalized email/letters).
- CRS / Congress Foundation: constituent correspondence tactics; offices need name, address, clear statement of what the constituent wants.
- Standard practice: staff ask “Where are you calling from?” and for name/address to verify constituency before counting the contact.

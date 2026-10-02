# COBRA-WATCH: testing and UI audit

What you'll do today: run the website on your laptop, test every feature, list what's broken or looks over-designed, and take screenshots. Takes about 3–4 hours. These steps assume Windows.

At the end you send Adi three things:
1. `bugs.md` (bug list)
2. `ui_audit.md` (design problems)
3. A `screenshots` folder

Two rules before you start:
- Never share or save real camera IP addresses from anywhere.
- Never open or connect to any camera that isn't yours.

---

## Part 1: install the tools (skip what you already have)

1. **Git**: https://git-scm.com/download/win, install with default options.
2. **Python 3.12**: https://www.python.org/downloads/. On the first installer screen, tick **"Add python.exe to PATH"** before clicking Install.
3. **Node.js LTS**: https://nodejs.org, the LTS version, default options.

Close any open terminal, open a new **Command Prompt**, and check:

```
git --version
python --version
node --version
```

All three should print a version number. If one says "not recognized", reinstall that one.

---

## Part 2: get the project

```
cd %USERPROFILE%
git clone https://github.com/Gokul0211/Geospatial-Camera-Exposure-Intelligence-Platform
cd Geospatial-Camera-Exposure-Intelligence-Platform
git checkout deploy-step1
```

Adi will send you a file called `public.db` (the cleaned database). Save it, then copy it into the project's `data` folder with this exact name:

```
copy %USERPROFILE%\Downloads\public.db data\surveillancewatch.db
```

It should say `1 file(s) copied.`

---

## Part 3: start the backend (Terminal 1)

In the same Command Prompt:

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
set PUBLIC_DEMO=1
uvicorn main:app --port 8000
```

The `pip install` takes a few minutes. When it's running you'll see:

```
Uvicorn running on http://127.0.0.1:8000
```

Leave this window open. Closing it stops the backend.

---

## Part 4: start the frontend (Terminal 2)

Open a **second** Command Prompt:

```
cd %USERPROFILE%\Geospatial-Camera-Exposure-Intelligence-Platform\frontend
npm install
npm run dev -- --host
```

When it's ready it shows a `Local:` address and a `Network:` address. Open the **Local** one in Chrome:

```
http://localhost:5173
```

The map should load. If it doesn't, screenshot both terminal windows and send them to Adi.

---

## Part 5: test every feature

Go through each item. For every problem you find, add an entry to `bugs.md` using the template below.

**Note:** the site runs in public demo mode, so some features are deliberately switched off: the AI brief, "ask a question" search, and saving verdicts. If one of these shows an error or "read-only", that's expected. Note it as **expected**, not a bug. But if it shows a broken or confusing screen to the visitor, that **is** worth noting, because a visitor won't know it's switched off.

### Map
- [ ] Switch to each city: Mumbai, Delhi, Bangalore, Hyderabad, Chennai, Kolkata, Pune, Ahmedabad, All India
- [ ] Zoom in and out, drag the map
- [ ] Click several cameras, check the popup opens and shows sensible info
- [ ] Check that no IP address appears anywhere (should be hidden)

### Alerts
- [ ] Open the live alerts panel
- [ ] Press the demo or trigger alert button, see what happens
- [ ] Click an alert, check its details

### Analytics
- [ ] Open the analytics panel, check charts load and numbers make sense
- [ ] Check the audit log or ledger section

### Attack simulator
- [ ] Open it, try each option, note what happens

### Search, filters, other panels
- [ ] Try every filter and dropdown
- [ ] Try the AI brief and the question box (expected to be disabled; note how it looks)
- [ ] Click every button you can find at least once

### Phone
- [ ] Phone and laptop on the same Wi-Fi
- [ ] On the phone, open the **Network** address from Terminal 2 (looks like `http://192.168.x.x:5173`)
- [ ] Check: does the map fit? Can you tap cameras? Is text readable? Do panels overlap?

### Bug template (copy into `bugs.md` for each problem)

```
## Bug N: short title
Where: (which panel / page)
Steps: 1) ... 2) ... 3) ...
Expected: what should have happened
Actual: what happened
Device: laptop / phone
Screenshot: screenshots/bug_N.png
Severity: broken / annoying / cosmetic
```

---

## Part 6: UI audit

Go through every screen again, this time only looking at the design. List anything that falls in these categories in `ui_audit.md`:

1. **Emoji used as buttons or labels** (e.g. "👍 TP")
2. **Glowing borders, neon colours, heavy shadows**
3. **Tiny ALL-CAPS labels** or text too small to read
4. **Confusing for a first-time visitor**: anything you didn't understand without asking
5. **Simulated data that looks real**: every place showing CVEs, owner type, login status or vulnerability details next to a map position. The device details are made up, so these are the spots that need a "simulated data" label.

Format for each entry:

```
## N. short title
Category: 1 / 2 / 3 / 4 / 5
Where: (panel and what you clicked to get there)
What's wrong: one line
Screenshot: screenshots/ui_N.png
```

---

## Part 7: screenshots for the paper

Make the Chrome window full screen (F11), close any open popups, and take clean screenshots of:

- [ ] Map view of one city (Mumbai), no popups open
- [ ] Map with one camera popup open
- [ ] Alerts panel with a few alerts
- [ ] Analytics panel

Save them as `paper_1.png` to `paper_4.png` in the `screenshots` folder. Windows shortcut: `Win + Shift + S`, then save.

---

## Part 8: send it

Put `bugs.md`, `ui_audit.md` and the `screenshots` folder in one folder, zip it, and send it to Adi.

To stop the app when done: press `Ctrl + C` in both terminal windows.

---

## If something goes wrong

- **`pip install` fails**: make sure Python is 3.12 (`python --version`). Screenshot the error, send to Adi.
- **`uvicorn` not recognized**: you forgot `venv\Scripts\activate`. Run it again from the `backend` folder.
- **Map loads but no cameras**: check `data\surveillancewatch.db` exists (Part 2). Check Terminal 1 for red errors.
- **Port already in use**: something else is running on 8000 or 5173. Restart the laptop and try again.
- **Anything else**: screenshot both terminals and the browser, send to Adi.

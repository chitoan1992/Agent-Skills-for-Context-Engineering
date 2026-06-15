#!/usr/bin/env python3
"""Generate a recurring reminder calendar (.ics) for the finding-purpose loop.

Turns the review cadence from continuous-evaluation.md into real, repeating
calendar reminders: a daily 2-line journal, a weekly notice, a 30-day cycle
review (score the rubric), a ~90-day convergence check, and a yearly arc
statement. The output is a standard iCalendar file importable into Google
Calendar, Apple Calendar, Outlook, etc. Reminders fire in the device's local
time (floating time), so they travel with the person.

Usage:
    python generate_reminders.py                 # starts tomorrow, English
    python generate_reminders.py --lang vi       # Vietnamese
    python generate_reminders.py --start 2026-06-16 --journal-time 21:00 \
        --lang vi --output purpose-reminders.ics

Standard library only; no dependencies.
"""

import argparse
import datetime as dt

# Cadence definition. Each entry: (uid, start_offset_days, time, duration_min, rrule, lang->(summary, description)).
# start_offset_days counts cycle days where day 1 = the --start date.
STRINGS = {
    "calname": {
        "en": "Purpose Beyond Self - Reminder Loop",
        "vi": "Muc dich song - Vong lap nhac nho",
    },
    "journal": {
        "en": ("Two-line journal: who did I serve? how did it feel?",
               "Write exactly two lines: who/what I served today + one honest "
               "sentence about how it felt. Rule: never skip two days in a row."),
        "vi": ("Nhat ky 2 dong: phuc vu ai? cam giac the nao?",
               "Viet dung 2 dong: hom nay phuc vu ai/viec gi + 1 cau cam giac "
               "that. Quy tac: khong bo 2 ngay lien tiep."),
    },
    "weekly": {
        "en": ("Re-read this week's journal - just notice, change nothing",
               "Read the last 7 entries. Adjust nothing this week; only notice "
               "patterns in the 'how it felt' column."),
        "vi": ("Doc lai nhat ky tuan - chi de y, khong sua",
               "Doc 7 dong gan nhat. Tuan nay khong chinh gi, chi de y mau hinh "
               "trong cot 'cam giac'."),
    },
    "cycle": {
        "en": ("Score the cycle /25 - then Scale / Refine / Pivot",
               "Day 30 review. Rate energy, service, sustainability, identity "
               "fit, growth (1-5 each). 20-25 SCALE, 12-19 REFINE one variable, "
               "below 12 PIVOT to a new hypothesis. Rewrite the purpose hypothesis."),
        "vi": ("Cham rubric /25 - roi Mo rong / Tinh chinh / Chuyen huong",
               "Soat ngay 30. Cham 5 chieu: nang luong, phuc vu, ben vung, dung "
               "voi minh, truong thanh (1-5). 20-25 MO RONG, 12-19 TINH CHINH mot "
               "bien, duoi 12 CHUYEN HUONG sang gia thuyet moi. Viet lai gia thuyet."),
    },
    "quarter": {
        "en": ("Convergence check - read the last 3 hypotheses side by side",
               "Are the last three cycle hypotheses pointing the same way? A "
               "repeating through-line is the next rung of the purpose ladder."),
        "vi": ("Soat hoi tu - doc 3 gia thuyet gan nhat canh nhau",
               "Ba gia thuyet gan nhat co cung chi mot huong khong? Mot mach "
               "xuyen suot lap lai chinh la bac thang muc dich tiep theo."),
    },
    "arc": {
        "en": ("Yearly arc statement - the through-line worth next year",
               "Write: 'Across this year's cycles the through-line was ___. The "
               "version I'm willing to give next year to is ___.'"),
        "vi": ("Cau tuyen ngon vong cung - mach dang gia ca nam toi",
               "Viet: 'Qua cac chu ky nam nay, mach xuyen suot la ___. Phien ban "
               "toi san long danh ca nam toi de theo duoi la ___.'"),
    },
}


def fold(line: str) -> str:
    """Fold a content line to <=75 octets per RFC 5545 (continuations start with a space)."""
    out = []
    while len(line.encode("utf-8")) > 75:
        # find a cut point at <=75 bytes
        cut = 75
        while len(line[:cut].encode("utf-8")) > 75:
            cut -= 1
        out.append(line[:cut])
        line = " " + line[cut:]
    out.append(line)
    return "\r\n".join(out)


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def vevent(uid, start, time_str, dur_min, rrule, summary, description, alarm_desc):
    hh, mm = time_str.split(":")
    dtstart = f"{start:%Y%m%d}T{int(hh):02d}{int(mm):02d}00"  # floating local time
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dt.datetime.utcnow():%Y%m%dT%H%M%S}Z",
        f"DTSTART:{dtstart}",
        f"DURATION:PT{dur_min}M",
        f"RRULE:{rrule}",
        fold(f"SUMMARY:{esc(summary)}"),
        fold(f"DESCRIPTION:{esc(description)}"),
        "BEGIN:VALARM",
        "TRIGGER:PT0M",
        "ACTION:DISPLAY",
        fold(f"DESCRIPTION:{esc(alarm_desc)}"),
        "END:VALARM",
        "END:VEVENT",
    ]
    return "\r\n".join(lines)


def build(start: dt.date, journal_time: str, lang: str) -> str:
    def s(key):
        return STRINGS[key][lang]

    weekly_start = start + dt.timedelta(days=(6 - start.weekday()) % 7)  # next Sunday (or today if Sunday)

    events = [
        vevent("purpose-daily-journal@finding-purpose", start, journal_time, 2,
               "FREQ=DAILY", *s("journal"), s("journal")[0]),
        vevent("purpose-weekly-notice@finding-purpose", weekly_start, "20:00", 5,
               "FREQ=WEEKLY;BYDAY=SU", *s("weekly"), s("weekly")[0]),
        vevent("purpose-cycle-review@finding-purpose", start + dt.timedelta(days=29), "20:00", 30,
               "FREQ=DAILY;INTERVAL=30", *s("cycle"), s("cycle")[0]),
        vevent("purpose-quarter-check@finding-purpose", start + dt.timedelta(days=89), "19:00", 60,
               "FREQ=DAILY;INTERVAL=90", *s("quarter"), s("quarter")[0]),
        vevent("purpose-yearly-arc@finding-purpose", start + dt.timedelta(days=364), "10:00", 240,
               "FREQ=YEARLY", *s("arc"), s("arc")[0]),
    ]

    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//finding-purpose-beyond-self//Reminder Loop//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        fold(f"X-WR-CALNAME:{STRINGS['calname'][lang]}"),
    ]
    return "\r\n".join(header) + "\r\n" + "\r\n".join(events) + "\r\nEND:VCALENDAR\r\n"


def main():
    p = argparse.ArgumentParser(description="Generate a recurring reminder calendar for the finding-purpose loop.")
    p.add_argument("--start", default=(dt.date.today() + dt.timedelta(days=1)).isoformat(),
                   help="Cycle day 1, YYYY-MM-DD (default: tomorrow).")
    p.add_argument("--journal-time", default="21:00", help="Daily journal reminder time HH:MM (default 21:00).")
    p.add_argument("--lang", choices=["en", "vi"], default="en", help="Reminder language (default en).")
    p.add_argument("--output", default="purpose-reminders.ics", help="Output .ics path.")
    args = p.parse_args()

    start = dt.date.fromisoformat(args.start)
    ics = build(start, args.journal_time, args.lang)
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        f.write(ics)
    print(f"Wrote {args.output}: 5 recurring reminders, cycle day 1 = {start.isoformat()}, lang={args.lang}")


if __name__ == "__main__":
    main()

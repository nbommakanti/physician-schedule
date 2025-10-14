import streamlit as st
from datetime import datetime, timedelta, UTC
import io
import pandas as pd

st.set_page_config(page_title="Schedule Generator", layout="centered")

st.title("Schedule Generator")
st.write("Enter your weekly schedule below, then generate a calendar (.ics) file that can be imported into Outlook, Google Calendar, or Apple Calendar.")

# --- Helper functions ---
WEEKDAY_MAP = {"Mon": 0, "Tues": 1, "Wed": 2, "Thur": 3, "Fri": 4}


def get_week_number_in_month(date):
    first_day = date.replace(day=1)
    days_from_first = (date - first_day).days
    return (days_from_first // 7) + 1


def sanitize_uid(text):
    return "".join(c for c in text if c.isalnum() or c in ("-", "_")).strip()


def create_event(uid, start, end, location):
    safe_uid = sanitize_uid(uid)
    return [
        "BEGIN:VEVENT",
        f"UID:{safe_uid}",
        f"DTSTAMP:{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{location}",
        f"LOCATION:{location}",
        "X-APPLE-TRAVEL-ADVISORY-BEHAVIOR:DISABLED",
        "END:VEVENT",
    ]


def generate_events(start_date, end_date, schedule):
    events = []
    current_date = start_date

    while current_date <= end_date:
        weekday = current_date.weekday()
        if weekday < 5:
            week_num = get_week_number_in_month(current_date)
            day_name = [k for k, v in WEEKDAY_MAP.items() if v == weekday][0]

            if week_num in schedule and day_name in schedule[week_num]:
                sessions = schedule[week_num][day_name]
                base_dt = datetime.combine(current_date, datetime.min.time())

                if sessions.get("AM") == sessions.get("PM"):
                    location = sessions["AM"]
                    start = base_dt.replace(hour=8, minute=0)
                    end = base_dt.replace(hour=17, minute=0)
                    uid = f"{start.strftime('%Y%m%dT%H%M%S')}-{location}@schedule"
                    events.extend(create_event(uid, start, end, location))
                else:
                    for session, location in sessions.items():
                        if session == "AM":
                            start = base_dt.replace(hour=8, minute=0)
                            end = base_dt.replace(hour=12, minute=0)
                        else:
                            start = base_dt.replace(hour=13, minute=0)
                            end = base_dt.replace(hour=17, minute=0)
                        uid = f"{start.strftime('%Y%m%dT%H%M%S')}-{location}@schedule"
                        events.extend(create_event(uid, start, end, location))
        current_date += timedelta(days=1)
    return events


def generate_ics(start_date, end_date, schedule):
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Schedule Generator//EN",
        "CALSCALE:GREGORIAN",
    ]
    ics_lines.extend(generate_events(start_date, end_date, schedule))
    ics_lines.append("END:VCALENDAR")
    return "\n".join(ics_lines)


def build_schedule_from_df(df):
    """Convert dataframe input to schedule dict structure."""
    schedule = {}
    for _, row in df.iterrows():
        week = int(row["Week"])
        ampm = row["AM/PM"].strip().upper()
        if week not in schedule:
            schedule[week] = {}
        for day in WEEKDAY_MAP.keys():
            if day not in schedule[week]:
                schedule[week][day] = {}
            value = str(row[day]).strip()
            if value:
                schedule[week][day][ampm] = value
    return schedule


# --- Streamlit UI ---
st.header("Weekly Schedule")

# Create editable grid with weeks 1–5 and AM/PM rows
default_data = []
for week in range(1, 6):
    default_data.append({"Week": week, "AM/PM": "AM", "Mon": "", "Tues": "", "Wed": "", "Thur": "", "Fri": ""})
    default_data.append({"Week": week, "AM/PM": "PM", "Mon": "", "Tues": "", "Wed": "", "Thur": "", "Fri": ""})

df = pd.DataFrame(default_data)

edited_df = st.data_editor(
    df,
    num_rows="fixed",
    use_container_width=True,
    key="schedule_editor",
    hide_index=True,  # hides row numbers
)

st.header("Date Range")
col1, col2 = st.columns(2)
start_date = col1.date_input("Start date", datetime(2025, 10, 1))
end_date = col2.date_input("End date", datetime(2025, 12, 31))

if start_date > end_date:
    st.error("Start date must be before end date.")
else:
    schedule = build_schedule_from_df(edited_df)

    if any(schedule[w][d].get("AM") or schedule[w][d].get("PM") for w in schedule for d in schedule[w]):
        ics_content = generate_ics(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time()),
            schedule,
        )
        buffer = io.StringIO(ics_content)
        st.download_button(
            label="Generate and Download .ics file",
            data=buffer.getvalue(),
            file_name="schedule.ics",
            mime="text/calendar",
        )
    else:
        st.info("Enter your schedule above to enable the download button.")

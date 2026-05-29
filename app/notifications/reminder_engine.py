from datetime import datetime, timedelta


def check_upcoming_events(events):
    upcoming = []

    now = datetime.now()

    for event in events:

        start = event.get("start", {}).get("dateTime")

        if start:

            event_time = datetime.fromisoformat(
                start.replace("Z", "+00:00")
            )

            difference = event_time - now.astimezone()

            if difference <= timedelta(minutes=30) and difference > timedelta(minutes=0):

                upcoming.append({
                    "title": event.get("summary"),
                    "starts_in_minutes": int(difference.total_seconds() / 60)
                })

    return upcoming

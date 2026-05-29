from winotify import Notification

toast = Notification(
    app_id="Calendar Reminder",
    title="Test",
    msg="Notifications are working!",
    duration="short"
)
toast.show()

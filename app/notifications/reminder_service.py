from plyer import notification


from winotify import Notification

def send_notification(title, message):
    toast = Notification(
        app_id="Calendar Reminder",
        title=title,
        msg=message,
        duration="short"
    )
    toast.show()
    
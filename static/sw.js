const CACHE = 'calendar-alarms-v1';

self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(clients.claim());
});

self.addEventListener('push', e => {
  if (!e.data) return;

  const data = e.data.json();

  const options = {
    body: data.body,
    icon: '/static/icon-192.png',
    badge: '/static/icon-192.png',
    vibrate: [500, 200, 500, 200, 500],
    requireInteraction: true,
    data: {
      event_id: data.event_id,
      url: '/alarm'
    },
    actions: [
      { action: 'dismiss', title: 'Dismiss' },
      { action: 'cancel_all', title: "Don't remind me again" }
    ]
  };

  e.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();

  const event_id = e.notification.data.event_id;

  if (e.action === 'cancel_all') {
    fetch('/api/cancel-reminders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_id })
    });
  }

  if (e.action === 'dismiss' || e.action === '') {
    e.waitUntil(
      clients.matchAll({ type: 'window' }).then(list => {
        if (list.length > 0) return list[0].focus();
        return clients.openWindow('/alarm');
      })
    );
  }
});

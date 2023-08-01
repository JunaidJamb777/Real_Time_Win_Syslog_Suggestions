import win32evtlog

# Replace "Application" with the desired log name (e.g., "System" or "Security").
log_type = "Application"

hand = win32evtlog.OpenEventLog(None, log_type)
flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
total_records = win32evtlog.GetNumberOfEventLogRecords(hand)

while True:
    events = win32evtlog.ReadEventLog(hand, flags, 0)
    if not events:
        break
    for event in events:
        # Process the event data here (e.g., extract information, perform NLP tasks).
        print(event.StringInserts)

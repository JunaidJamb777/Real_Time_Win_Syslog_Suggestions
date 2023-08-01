import win32evtlog
import csv
from datetime import datetime
from transformers import BertTokenizer, BertForSequenceClassification
import torch

# Replace "Application" with the desired log name (e.g., "System" or "Security").
log_type = "Application"

hand = win32evtlog.OpenEventLog(None, log_type)
flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
total_records = win32evtlog.GetNumberOfEventLogRecords(hand)

# Get the current date and time to include in the CSV file name
current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")

# Specify the CSV file name with the date and time format
csv_file = f"{current_datetime}_syslog.csv"

# Define the column headers for the CSV file
field_names = ["Timestamp", "Hostname", "Log Level", "Log Message", "Classification"]

# Load pre-trained BERT model and tokenizer
model_name = "bert-base-uncased"  # You can choose a different pre-trained BERT model here
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name)

# Open the CSV file in write mode with utf-8 encoding
with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
    csv_writer = csv.DictWriter(csvfile, fieldnames=field_names)

    # Write the header row to the CSV file
    csv_writer.writeheader()

    while True:
        events = win32evtlog.ReadEventLog(hand, flags, 0)
        if not events:
            break
        for event in events:
            # Extract event data from the event object
            timestamp = event.TimeGenerated.Format(" %b %d %Y %H:%M:%S")
            hostname = event.ComputerName

            # Map event type to log level
            event_type = event.EventType
            log_level_mapping = {
                win32evtlog.EVENTLOG_SUCCESS: "Information",
                win32evtlog.EVENTLOG_ERROR_TYPE: "Error",
                win32evtlog.EVENTLOG_WARNING_TYPE: "Warning",
                win32evtlog.EVENTLOG_INFORMATION_TYPE: "Information",
            }
            log_level = log_level_mapping.get(event_type, "Unknown")

            log_message = event.StringInserts

            # Tokenize the input text
            inputs = tokenizer(log_message, return_tensors="pt", padding=True, truncation=True)

            # Run the BERT model for inference
            outputs = model(**inputs)

            # Get the predicted label (example: binary classification)
            predicted_label = torch.argmax(outputs.logits).item()

            # Get the name of the label (example: in a binary classification problem, "0" and "1" can be mapped to "Negative" and "Positive")
            label_names = ["Negative", "Positive"]
            classification = label_names[predicted_label]

            # Prepare the event data as a dictionary
            event_data = {
                "Timestamp": timestamp,
                "Hostname": hostname,
                "Log Level": log_level,
                "Log Message": log_message,
                "Classification": classification,
            }

            # Write the event data to the CSV file
            csv_writer.writerow(event_data)

print("Data saved to CSV file:", csv_file)

from flask import Flask, render_template, request, session
import win32evtlog
import csv
from datetime import datetime
import openai
import time

app = Flask(__name__)
import secrets

# Generate a random secret key
secret_key = secrets.token_hex(16)

# Print the generated secret key
print(secret_key)

app.secret_key = secret_key
hand = None
flags = None
total_records = None

# Get the current date and time to include in the CSV file name
current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")

# Specify the CSV file name with the date and time format
csv_file = f"{current_datetime}_syslog.csv"

# Define the column headers for the CSV file
field_names = ["Timestamp", "Hostname", "Log Level", "Log Message", "Suggestion"]

# Helper function to get a suggestion for an error message using the GPT-3.5 API with retry
def get_suggestion_with_retry(error_message, retry_attempts=3):
    for i in range(retry_attempts):
        try:
            prompt = f"Error message: {error_message}\nSuggestion:"
            response = openai.Completion.create(engine="text-davinci-002", prompt=prompt, max_tokens=50, api_key=session.get("openapi_key"))
            return response.choices[0].text.strip()
        except openai.error.RateLimitError:
            # Wait for 20 seconds before retrying
            time.sleep(20)
    # If retries fail, return an empty suggestion
    return ""

@app.route("/", methods=["GET", "POST"])
def index():
    global hand, flags, total_records

    # Code for loading log names and types (if applicable)
    log_names = ["Application", "System", "Security"]  # Replace with the actual log names
    log_types = ["Information", "Error", "Warning", "Unknown"]  # Replace with the actual log types

    filtered_logs = []  # Initialize filtered_logs as an empty list

    if request.method == "POST":
        # Get user input from the form
        openapi_key = request.form["openapi_key"]
        log_name = request.form["log_name"]
        log_type = request.form["log_type"]
        filter_range = request.form["filter_range"]
        filter_date = request.form["filter_date"]
        filter_time = request.form["filter_time"]

        # Combine date and time to form the timestamp
        filter_timestamp = f"{filter_date} {filter_time}"

        # Store OpenAI API key in the session
        session["openapi_key"] = openapi_key

        # Set the Flask app secret key to the OpenAI API key
        app.secret_key = openapi_key

        # Set the OpenAI API key for making API calls
        openai.api_key = openapi_key

        # Initialize the event log if it's not already initialized
        if hand is None:
            hand = win32evtlog.OpenEventLog(None, log_name)
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            total_records = win32evtlog.GetNumberOfEventLogRecords(hand)

        # Filter logs based on the user's input
        filtered_logs = []
        while True:
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            if not events:
                break
            for event in events:
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

                # Apply filters based on user input
                if filter_range == "all" or filter_timestamp == timestamp:
                    filtered_logs.append({
                        "Timestamp": timestamp,
                        "Hostname": hostname,
                        "Log Level": log_level,
                        "Log Message": log_message,
                    })

        # Generate ChatGPT suggestions for each log message
        for log in filtered_logs:
            log_message = log["Log Message"]
            suggestion = get_suggestion_with_retry(log_message)
            log["Suggestion"] = suggestion

        # Write the filtered logs to the CSV file
        with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.DictWriter(csvfile, fieldnames=field_names)
            csv_writer.writeheader()
            for log in filtered_logs:
                csv_writer.writerow(log)

    return render_template("index.html", log_names=log_names, log_types=log_types, logs_data=filtered_logs)

if __name__ == "__main__":
    app.run(debug=True)
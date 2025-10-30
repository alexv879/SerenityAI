import csv

def log_session_data(session_id: str, module: str, duration: int, exit_phrase: str):
    """
    Log session analytics to a CSV file.
    """
    with open("session_analytics.csv", "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([session_id, module, duration, exit_phrase])

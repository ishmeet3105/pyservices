from datetime import datetime, timezone

def determine_campaign_status(start_time, end_time):
    try:
        now = datetime.now(timezone.utc)

        # Convert strings to aware datetimes if needed
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        if start_time <= now < end_time:
            return True
        elif now >= end_time:
            return False
        return None
    except Exception as e:
        print(f"Error in determine_campaign_status: {e}")
        return None

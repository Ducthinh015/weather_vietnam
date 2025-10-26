from backend.services.forecast_service import forecast_next_hours

def test_forecast_format():
    sample = {
        "hourly": [
            {"temp": 300.0, "humidity": 60},
        ] * 48
    }
    out = forecast_next_hours(sample, hours=3)
    assert len(out) == 3
    assert set(out[0].keys()) == {"after_hours", "temperature", "humidity"}


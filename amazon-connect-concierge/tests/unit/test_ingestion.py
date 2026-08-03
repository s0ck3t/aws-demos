import os
import sys
import pytest

# Add amazon-connect-concierge root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.utils.profile_helpers import format_clickstream_profile_object, parse_profile_recommendations


def test_format_clickstream_profile_object_valid():
    sample_event = {
        "event_id": "evt-999",
        "email": "user@example.com",
        "phone": "+15550199",
        "event_type": "view_product",
        "sku": "SKU-AUDIO-101"
    }

    result = format_clickstream_profile_object(sample_event)
    assert result["ObjectTypeName"] == "WebClickstreamEvent"
    assert "evt-999" in result["Object"]
    assert "user@example.com" in result["Object"]


def test_format_clickstream_profile_object_missing_keys():
    invalid_event = {
        "email": "user@example.com"
    }

    with pytest.raises(ValueError, match="Missing required clickstream event key"):
        format_clickstream_profile_object(invalid_event)


def test_parse_profile_recommendations():
    raw_profile = {
        "ProfileId": "prof-12345",
        "Attributes": {
            "EmailAddress": "user@example.com",
            "PhoneNumber": "+15550199",
            "LastViewedSKU": "SKU-SMART-201",
            "RecommendedCategory": "Wearable Accessories",
            "PropensityScore": "0.94"
        }
    }

    parsed = parse_profile_recommendations(raw_profile)
    assert parsed["profile_id"] == "prof-12345"
    assert parsed["last_viewed_sku"] == "SKU-SMART-201"
    assert parsed["recommended_category"] == "Wearable Accessories"
    assert parsed["propensity_score"] == 0.94
    assert "Wearable Accessories" in parsed["prompt_context"]

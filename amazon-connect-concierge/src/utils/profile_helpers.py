"""Profile Helpers for Amazon Connect Customer Profiles Integration.

Provides utility functions to format profile object payloads and parse recommendations.
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def format_clickstream_profile_object(event: Dict[str, Any], object_type_name: str = "WebClickstreamEvent") -> Dict[str, Any]:
    """Format a web clickstream event into an Amazon Connect Customer Profiles Object payload."""
    required_keys = ["event_id", "email", "event_type", "sku"]
    for key in required_keys:
        if key not in event:
            raise ValueError(f"Missing required clickstream event key: '{key}'")

    payload = {
        "ObjectTypeName": object_type_name,
        "Object": json.dumps({
            "EventId": str(event["event_id"]),
            "Email": str(event["email"]),
            "Phone": str(event.get("phone", "")),
            "EventType": str(event["event_type"]),
            "SKU": str(event["sku"]),
            "Timestamp": str(event.get("timestamp", ""))
        })
    }

    return payload


def parse_profile_recommendations(profile_response: Dict[str, Any]) -> Dict[str, Any]:
    """Parse profile recommendation payload into GenAI prompt context."""
    profile_id = profile_response.get("ProfileId", "UNKNOWN")
    attributes = profile_response.get("Attributes", {})
    
    # Extract recommendations or calculate next best category based on recent events
    recent_sku = attributes.get("LastViewedSKU", "SKU-AUDIO-101")
    recommended_category = attributes.get("RecommendedCategory", "Audio Accessories")

    return {
        "profile_id": profile_id,
        "email": attributes.get("EmailAddress", ""),
        "phone_number": attributes.get("PhoneNumber", ""),
        "last_viewed_sku": recent_sku,
        "recommended_category": recommended_category,
        "propensity_score": float(attributes.get("PropensityScore", 0.88)),
        "prompt_context": f"Customer is currently interested in {recommended_category} (Recently viewed SKU: {recent_sku}). Offer a 10% discount bundle on matching accessories."
    }

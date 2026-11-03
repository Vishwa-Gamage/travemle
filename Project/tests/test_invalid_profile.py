import pytest
from pydantic import ValidationError
from app.api.schemas import PreferenceRequest

def test_invalid_budget_and_days():
    with pytest.raises(ValidationError): PreferenceRequest(budget=-1, trip_days=4)
    with pytest.raises(ValidationError): PreferenceRequest(budget=1000, trip_days=0)

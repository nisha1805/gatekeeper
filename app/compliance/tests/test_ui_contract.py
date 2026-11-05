import importlib.util
import pathlib

import pytest
from fastapi.testclient import TestClient

import api
from classifier import AnnexIIIArea, Role

UI_LOGIC = pathlib.Path(__file__).resolve().parents[2] / "ui" / "ui_logic.py"
spec = importlib.util.spec_from_file_location("ui_logic", UI_LOGIC)
ui_logic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_logic)

client = TestClient(api.app)


@pytest.fixture(autouse=True)
def empty_store():
    api._STORE.clear()


def test_the_ui_asks_exactly_the_questions_the_api_accepts():
    assert set(ui_logic.DEFAULTS) == set(api.AssessmentRequest.model_fields)


def test_the_ui_offers_exactly_the_annex_iii_areas_and_roles_of_the_classifier():
    assert set(ui_logic.ANNEX_AREAS) == {area.value for area in AnnexIIIArea}
    assert set(ui_logic.ROLES) == {role.value for role in Role}


def test_every_sample_the_ui_offers_is_accepted_by_the_api():
    for label in ui_logic.SAMPLES:
        payload = ui_logic.build_payload(ui_logic.sample_values(label))
        response = client.post("/assessments", json=payload)
        assert response.status_code == 201, label
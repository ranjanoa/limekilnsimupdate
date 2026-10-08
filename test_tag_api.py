import requests
import json
import time

BASE_URL = "http://localhost:8080"

def test_endpoints():
    print("Testing /api/tags GET...")
    r = requests.get(f"{BASE_URL}/api/tags")
    assert r.status_code == 200, f"Status: {r.status_code}"
    data = r.json()
    tags = data if isinstance(data, list) else data.get("tags", [])
    print(f"Loaded {len(tags)} tags. Total setpoints: {sum(1 for t in tags if t['category'] == 'setpoint')}")

    # Test toggling a tag source to 'local'
    feed_tag = next(t for t in tags if t["tag_id"] == "Opt_FeedRate_SP")
    print(f"Original feed source: {feed_tag['source']}")
    r = requests.post(f"{BASE_URL}/api/tags/toggle", json={"tag_id": "Opt_FeedRate_SP", "source": "local"})
    assert r.status_code == 200
    res = r.json()
    assert res["status"] in ["ok", "success"]
    assert res["source"] == "local"
    print("Successfully toggled Opt_FeedRate_SP to local!")

    # Test setting local value
    r = requests.post(f"{BASE_URL}/api/tags/value", json={"tag_id": "Opt_FeedRate_SP", "value": 282.5})
    assert r.status_code == 200
    res = r.json()
    assert res["status"] in ["ok", "success"]
    assert res["value"] == 282.5
    print("Successfully set local setpoint to 282.5 t/h!")

    # Test creating custom tag
    custom_tag = {
        "tag_id": "CUSTOM_TAD_Draft",
        "name": "Tertiary Air Duct Differential Draft",
        "hmi_tag": "PDT-405",
        "category": "measurement",
        "source": "opc_ua",
        "opc_node_id": "ns=2;s=Kiln3.Telemetry.TAD_DiffDraft",
        "opc_direction": "read",
        "unit": "mbar",
        "type": "float",
        "min": -5.0,
        "max": 5.0,
        "default": 0.5
    }
    r = requests.post(f"{BASE_URL}/api/tags/create", json=custom_tag)
    assert r.status_code == 200
    assert r.json()["status"] in ["ok", "success"]
    print("Successfully created custom tag!")

    # Verify custom tag in list
    r = requests.get(f"{BASE_URL}/api/tags")
    res_data = r.json()
    tags = res_data if isinstance(res_data, list) else res_data.get("tags", [])
    assert any(t["tag_id"] == "CUSTOM_TAD_Draft" for t in tags)
    print("Custom tag verified in tag list!")

    # Test deleting custom tag
    r = requests.post(f"{BASE_URL}/api/tags/delete", json={"tag_id": "CUSTOM_TAD_Draft"})
    assert r.status_code == 200
    assert r.json()["status"] in ["ok", "success"]
    print("Successfully deleted custom tag!")

    # Test toggling feed back to opc_ua
    r = requests.post(f"{BASE_URL}/api/tags/toggle", json={"tag_id": "Opt_FeedRate_SP", "source": "opc_ua"})
    assert r.status_code == 200
    assert r.json()["status"] in ["ok", "success"]
    print("Restored feed tag to opc_ua.")

    # Test OPC UA endpoint test
    r = requests.post(f"{BASE_URL}/api/opc/test")
    assert r.status_code == 200
    res = r.json()
    assert res["status"] in ["ok", "success"]
    print("OPC UA Server test result:", res)

    print("\nALL API ENDPOINT TESTS PASSED SUCCESSFULLY! [OK]")

if __name__ == "__main__":
    test_endpoints()

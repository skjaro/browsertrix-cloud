import requests

from .conftest import API_PREFIX


def test_delete_org_non_superadmin(crawler_auth_headers, default_org_id):
    # Assert that non-superadmin can't delete org
    r = requests.delete(
        f"{API_PREFIX}/orgs/{default_org_id}", headers=crawler_auth_headers
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "Not Allowed"


def test_delete_org_superadmin(admin_auth_headers, default_org_id):
    # Ensure workflows and other data exists in org prior to deletion
    r = requests.get(
        f"{API_PREFIX}/orgs/{default_org_id}/crawlconfigs", headers=admin_auth_headers
    )
    assert r.status_code == 200
    assert r.json()["total"] > 0

    r = requests.get(
        f"{API_PREFIX}/orgs/{default_org_id}/all-crawls", headers=admin_auth_headers
    )
    assert r.status_code == 200
    assert r.json()["total"] > 0

    # Delete org and its data
    r = requests.delete(
        f"{API_PREFIX}/orgs/{default_org_id}", headers=admin_auth_headers
    )
    assert r.status_code == 200
    assert r.json()["deleted"]

    # Ensure data got deleted
    r = requests.get(
        f"{API_PREFIX}/orgs/{default_org_id}/crawlconfigs", headers=admin_auth_headers
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0

    r = requests.get(
        f"{API_PREFIX}/orgs/{default_org_id}/all-crawls", headers=admin_auth_headers
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0

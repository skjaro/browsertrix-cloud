import json
import requests
import time

import pytest

from .conftest import API_PREFIX


LINES_TO_TEST = 10


@pytest.mark.parametrize(
    "log_level, context",
    [
        # No filtering
        (None, None),
        # Filter log level
        ("info", None),
        # Filter context
        ("None", "general"),
        # Filter both
        ("info", "general"),
    ],
)
def test_stream_crawl_logs_running(
    admin_auth_headers, default_org_id, large_crawl_id, log_level, context
):
    """Test that streaming logs while crawl is running works."""
    api_url = f"{API_PREFIX}/orgs/{default_org_id}/crawls/{large_crawl_id}/logs"
    if log_level and context:
        api_url = api_url + f"?log_level={log_level}&context={context}"
    elif log_level:
        api_url = api_url + f"?log_level={log_level}"
    elif context:
        api_url = api_url + f"?context={context}"

    with requests.get(api_url, headers=admin_auth_headers, stream=True) as r:
        assert r.status_code == 200

        line_index = 0
        if not r.content:
            time.sleep(5)

        for line in r.iter_lines():
            if line_index >= LINES_TO_TEST:
                r.close()
                continue

            line = line.decode("utf-8")
            log_line_dict = json.loads(line)

            assert log_line_dict["logLevel"]
            if log_level:
                assert log_line_dict["logLevel"] == log_level

            assert log_line_dict["timestamp"]

            assert log_line_dict["context"]
            if context:
                assert log_line_dict["context"] == context

            assert log_line_dict["details"] or log_line_dict["details"] == {}

            line_index += 1


@pytest.mark.parametrize(
    "log_level, context",
    [
        # No filtering
        (None, None),
        # Filter log level
        ("info", None),
        # Filter context
        ("None", "general"),
        # Filter both
        ("info", "general"),
    ],
)
def test_stream_crawl_logs_wacz(
    admin_auth_headers,
    default_org_id,
    large_crawl_id,
    large_crawl_finished,
    log_level,
    context,
):
    """Test that streaming logs after crawl concludes from WACZs works."""
    api_url = f"{API_PREFIX}/orgs/{default_org_id}/crawls/{large_crawl_id}/logs"
    if log_level and context:
        api_url = api_url + f"?log_level={log_level}&context={context}"
    elif log_level:
        api_url = api_url + f"?log_level={log_level}"
    elif context:
        api_url = api_url + f"?context={context}"

    with requests.get(api_url, headers=admin_auth_headers, stream=True) as r:
        assert r.status_code == 200

        last_timestamp = None
        line_index = 0
        for line in r.iter_lines():
            if line_index >= LINES_TO_TEST:
                r.close()
                continue

            line = line.decode("utf-8")
            log_line_dict = json.loads(line)

            assert log_line_dict["logLevel"]
            if log_level:
                assert log_line_dict["logLevel"] == log_level

            assert log_line_dict["timestamp"]

            assert log_line_dict["context"]
            if context:
                assert log_line_dict["context"] == context
            assert log_line_dict["details"] or log_line_dict["details"] == {}

            timestamp = log_line_dict["timestamp"]
            if last_timestamp:
                assert timestamp > last_timestamp
            last_timestamp = timestamp

            line_index += 1

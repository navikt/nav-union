from unittest.mock import Mock

import pytest
import requests

from nav_union import slack


@pytest.fixture
def task_environment():
    # Register the wrapper without invoking Flyte's execution machinery.
    return Mock(task=Mock(side_effect=lambda task: task))


def test_success_returns_result_without_notifying(task_environment, monkeypatch):
    notify = Mock()
    monkeypatch.setattr(slack, "send_slack_message", notify)

    def task():
        """An example task."""
        return 42

    wrapped = slack.flyte_task(task_environment, "alerts")(task)

    task_environment.task.assert_called_once_with(wrapped)
    assert wrapped.__name__ == task.__name__
    assert wrapped.__doc__ == task.__doc__
    assert wrapped() == 42
    notify.assert_not_called()


@pytest.mark.parametrize("notify_on_failure", [True, False])
def test_failure_respects_notification_setting(
    task_environment, monkeypatch, notify_on_failure
):
    notify = Mock()
    monkeypatch.setattr(slack, "send_slack_message", notify)

    @slack.flyte_task(task_environment, "alerts", notify_on_failure=notify_on_failure)
    def failing_task():
        raise ValueError("task failed")

    with pytest.raises(Exception, match="task failed"):
        failing_task()

    if notify_on_failure:
        notify.assert_called_once_with(
            channel_name="alerts",
            message="❌ Feil i failing_task! Sjekk logger i Union ❌",
        )
    else:
        notify.assert_not_called()


def test_failure_notifies_by_default(task_environment, monkeypatch):
    notify = Mock()
    monkeypatch.setattr(slack, "send_slack_message", notify)

    @slack.flyte_task(task_environment, "alerts")
    def failing_task():
        raise RuntimeError("task failed")

    with pytest.raises(Exception, match="task failed"):
        failing_task()

    notify.assert_called_once()


def test_send_slack_message_uses_token_and_payload(monkeypatch):
    monkeypatch.setenv("SLACK_TOKEN", "test-token")
    post = Mock()
    monkeypatch.setattr(slack.requests, "post", post)

    slack.send_slack_message("alerts", "Something happened")

    post.assert_called_once()
    assert post.call_args.kwargs["headers"] == {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json",
    }
    assert post.call_args.kwargs["json"] == {
        "channel": "#alerts",
        "text": "Something happened",
    }
    post.return_value.raise_for_status.assert_called_once_with()


def test_send_slack_message_propagates_http_errors(monkeypatch):
    monkeypatch.setenv("SLACK_TOKEN", "test-token")
    post = Mock()
    post.return_value.raise_for_status.side_effect = requests.HTTPError("HTTP failure")
    monkeypatch.setattr(slack.requests, "post", post)

    with pytest.raises(requests.HTTPError, match="HTTP failure"):
        slack.send_slack_message("alerts", "Something happened")

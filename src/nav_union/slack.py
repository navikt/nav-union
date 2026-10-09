import requests
import os

from collections.abc import Callable
from functools import wraps

from flyte import TaskEnvironment

def send_slack_message(channel_name: str, message: str) -> None:
    slack_token = os.environ["SLACK_TOKEN"]
    url = "http://slack.com/api/chat.postMessage"
    headers = {"Authorization": f"Bearer {slack_token}", "Content-Type": "application/json"}
    payload = {"channel": f"#{channel_name}", "text": message}

    response = requests.post(url=url, headers=headers, json=payload)
    response.raise_for_status()


def flyte_task(task_environment: TaskEnvironment, channel_name: str, notify_on_failure: bool = True):
    def decorator(task: Callable[[], None]):
        @wraps(task)
        def wrapped():
            try:
                return task()
            except Exception as error:
                if notify_on_failure:
                    task_name = task.__name__
                    slack_message = f"❌ Feil i {task_name}! Sjekk logger i Union ❌"
                    send_slack_message(channel_name=channel_name, message=slack_message)

                raise Exception(error)

        return task_environment.task(wrapped)

    return decorator
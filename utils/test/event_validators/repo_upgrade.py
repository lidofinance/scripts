#!/usr/bin/python3

from typing import NamedTuple, Tuple

from brownie.network.event import EventDict
from .common import validate_events_chain


class RepoUpgrade(NamedTuple):
    version_id: int
    semantic_version: Tuple[int, int, int]


def validate_repo_upgrade_event(event: EventDict, ru: RepoUpgrade):
    _repo_upgrade_events_chain = ['LogScriptCall', 'NewVersion']

    validate_events_chain([e.name for e in event], _repo_upgrade_events_chain)

    assert event.count('NewVersion') == 1

    assert event['NewVersion']['versionId'] == ru.version_id
    assert event['NewVersion']['semanticVersion'] == ru.semantic_version

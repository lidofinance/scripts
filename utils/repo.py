from utils.config import contracts


def _add_implementation_to_repo(repo, version, address, content_uri):
    return (
        repo.address,
        repo.newVersion.encode_input(
            version,
            address,
            content_uri
        )
    )


def add_implementation_to_lido_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.lido_app_repo, version, address, content_uri)


def add_implementation_to_nos_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.nos_app_repo, version, address, content_uri)


def add_implementation_to_voting_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.voting_app_repo, version, address, content_uri)


def add_implementation_to_oracle_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.oracle_app_repo, version, address, content_uri)

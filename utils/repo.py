from utils.config import contracts


def _add_implementation_to_repo(repo, version, address, content_uri):
    return (repo.address, repo.newVersion.encode_input(version, address, content_uri))


def add_implementation_to_lido_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.lido_app_repo, version, address, content_uri)


def add_implementation_to_nor_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.nor_app_repo, version, address, content_uri)


def add_implementation_to_sdvt_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.simple_dvt_app_repo, version, address, content_uri)


def add_implementation_to_sandbox_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.sandbox_repo, version, address, content_uri)


def add_implementation_to_voting_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.voting_app_repo, version, address, content_uri)


def create_new_app_repo(name, manager, version, address, content_uri):
    apm_registry = contracts.apm_registry

    return (
        apm_registry.address,
        apm_registry.newRepoWithVersion.encode_input(name, manager, version, address, content_uri),
    )

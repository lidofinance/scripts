import requests
import io
import re

from utils.config import (
    get_web3_storage_token,
    get_infura_io_keys,
)


def upload_str_to_infura_io(text) -> str:
    text_bytes = text.encode("utf-8")
    text_file = io.BytesIO(text_bytes)
    files = {"file": text_file}
    (projectId, projectSecret) = get_infura_io_keys()

    endpoint = "https://ipfs.infura.io:5001"

    response = requests.post(endpoint + "/api/v0/add?cid-version=1", files=files, auth=(projectId, projectSecret))
    response.raise_for_status()
    response_json = response.json()

    return response_json.get("Hash")


def upload_str_to_web3_storage(text) -> str:
    text_bytes = text.encode("utf-8")
    text_file = io.BytesIO(text_bytes)
    web3_storage_token = get_web3_storage_token()

    endpoint = "https://api.web3.storage/upload"
    headers = {"Authorization": f"Bearer {web3_storage_token}", "Content-Type": "application/x-directory"}

    response = requests.post(endpoint, headers=headers, data=text_file)
    response.raise_for_status()
    response_json = response.json()

    return response_json.get("cid")


def upload_str_to_ipfs(text) -> str:
    return upload_str_to_web3_storage(text)


def get_cid_form_from_str(text) -> str:
    cid_reg = "(Qm[1-9A-HJ-NP-Za-km-z]{44,128}|b[A-Za-z2-7]{58,128}|B[A-Z2-7]{58,128}|z[1-9A-HJ-NP-Za-km-z]{48,128}|F[0-9A-F]{50,128})$"

    return re.search(cid_reg, text).group()

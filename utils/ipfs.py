import aiohttp
import asyncio
import io
import re
import requests
from typing import Tuple, TypedDict
from os import linesep

from ipfs_cid import cid_sha256_hash

from utils.config import get_web3_storage_token
from utils.evm_script import checksum_verify

#  https://github.com/multiformats/multibase/blob/master/multibase.csv
#  IPFS has two CID formats v0 and v1, v1 supports different encodings, defaults are:
#  CIDv0:
#    base58btc              Qm ✓ QmRKs2ZfuwvmZA3QAWmCqrGUjV9pxtBUDP3wuc6iVGnjA2
#  CIDv1:
#    base16                  f ✓ f017012202c5f688262e0ece8569aa6f94d60aad55ca8d9d83734e4a7430d0cff6588ec2b
#    base16upper             F ✓ F017012202C5F688262E0ECE8569AA6F94D60AAD55CA8D9D83734E4A7430D0CFF6588EC2B
#    base32upper             B ✓ BAFYBEIBML5UIEYXA5TUFNGVG7FGWBKWVLSUNTWBXGTSKOQYNBT7WLCHMFM
#    base32                  b ✓ bafybeibml5uieyxa5tufngvg7fgwbkwvlsuntwbxgtskoqynbt7wlchmfm
#    base58btc               z ✓ zdj7WYR7PzjmRQNRsMKuFipiE73MhMGgRbc5hTUaQVPJiMdKx
#    base64                  m ✓ mAXASICxfaIJi4OzoVpqm+U1gqtVcqNnYNzTkp0MNDP9liOwr
#    base64url               u ✓ uAXASICxfaIJi4OzoVpqm-U1gqtVcqNnYNzTkp0MNDP9liOwr
#    base64urlpad            U ✓ UAXASICxfaIJi4OzoVpqm-U1gqtVcqNnYNzTkp0MNDP9liOwr
#

REG_CID_0_58_BTC = r"Qm[1-9A-HJ-NP-Za-km-z]{44,128}"
REG_CID_1_16 = r"[fF][0-9a-zA-F]{50,128}"  # case-insensitive
REG_CID_1_32 = r"[bB][a-zA-Z2-7]{58,128}"  # case-insensitive
REG_CID_1_58_BTC = r"z[1-9A-HJ-NP-Za-km-z]{48,128}"
REG_CID_1_64 = r"m[+A-Za-z0-9/]{40,128}"
REG_CID_1_64_URL = r"u[-A-Za-z0-9_]{40,128}"
REG_CID_1_64_URLPAD = r"U[-A-Za-z0-9_]{40,128}={0,3}"

REG_CID_DEFAULT = rf"\b({REG_CID_0_58_BTC}|{REG_CID_1_16}|{REG_CID_1_32}|{REG_CID_1_58_BTC}|{REG_CID_1_64}|{REG_CID_1_64_URL}|{REG_CID_1_64_URLPAD})\b"
REG_ETH_ADDRESS = r"\b(0x[a-fA-F0-9]{40})\b"

REG_VOTE_CID = rf"\b({REG_CID_1_32})\b"
VOTE_CID_PREFIX = "lidovoteipfs://"
REG_VOTE_CID_WITH_PREFIX_LAST = rf"\b{VOTE_CID_PREFIX}{REG_VOTE_CID}\s*$"


class IPFSUploadResult(TypedDict):
    cid: str
    text: str
    messages: list[Tuple[str, str]]


# upload text to web3.storage ipfs
def _upload_str_to_web3_storage(text: str) -> str:
    text_bytes = text.encode("utf-8")
    text_file = io.BytesIO(text_bytes)
    web3_storage_token = get_web3_storage_token()

    endpoint = "https://api.web3.storage/upload"
    headers = {"Authorization": f"Bearer {web3_storage_token}", "Content-Type": "application/x-directory"}

    response = requests.post(endpoint, headers=headers, data=text_file)
    response.raise_for_status()
    response_json = response.json()

    return response_json.get("cid")


def _upload_str_to_ipfs(text: str) -> str:
    return _upload_str_to_web3_storage(text)


# calculate cid hash from utf8 str
def calculate_cid_hash(text: str) -> str:
    data = bytes(text, "utf-8")
    return cid_sha256_hash(data)


# fetching url status
async def _fetch_status(session, url: str) -> int:
    async with session.get(url) as response:
        return response.status


# fetch cid from different api concurrency
async def _fetch_cid_status_from_ipfs_async(cid: str) -> int:
    if not cid:
        return 404

    request_urls = [
        f"https://{cid}.ipfs.w3s.link",  # faster for uploaded files
        f"https://api.web3.storage/status/{cid}",  # much faster for not uploaded files
    ]

    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(_fetch_status(session, url)) for url in request_urls]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()

        for task in done:
            return task.result()


def verify_ipfs_description(text: str) -> list[Tuple[str, str]]:
    messages: list[Tuple[str, str]] = []
    if not text:
        messages.append(
            (
                "error",
                (
                    "You provided an empty string as description. If you provide text as a description, "
                    "it will help users to make a voting decision. The description is stored on the IPFS network"
                    "and take fixed space in the script regardless of text length."
                ),
            )
        )

    ugly_address_raw_groups = re.findall(rf"([^`]{REG_ETH_ADDRESS}|{REG_ETH_ADDRESS}[^`])", f" {text} ")

    if ugly_address_raw_groups:
        address_raw = list(map(lambda x: x[1] or x[2], ugly_address_raw_groups))
        messages.append(
            (
                "warning",
                (
                    "You have wallet addresses in description which has no Markdown style. "
                    "You could use inline code block to make it looks better. "
                    "You need to add '`' before and after the address. Here is the list of addresses:\n"
                    f"{linesep.join(address_raw)}"
                ),
            )
        )
    all_address_raw_groups = re.findall(rf"{REG_ETH_ADDRESS}", f" {text} ")

    if all_address_raw_groups:
        wrong_address_raw = list(filter(lambda address: not checksum_verify(address), all_address_raw_groups))
        messages.append(
            (
                "error",
                (
                    "You have wallet addresses in description which has wrong hash sum. "
                    "Here is the list of addresses:\n"
                    f"{linesep.join(wrong_address_raw)}"
                ),
            )
        )
    ugly_cid_raw_groups = re.findall(rf"([^`]{REG_CID_DEFAULT}|{REG_CID_DEFAULT}[^`])", f" {text} ")
    if ugly_cid_raw_groups:
        cid_raw = list(map(lambda x: x[1] or x[2], ugly_cid_raw_groups))
        messages.append(
            (
                "warning",
                (
                    "You have CIDs in description which has no Markdown style. "
                    "You could use inline code block to make it looks better. "
                    "You need to add '`' before and after CID. Here is the list of CID:\n"
                    f"{linesep.join(cid_raw)}"
                ),
            )
        )
    return messages


def fetch_cid_status_from_ipfs(cid: str):
    return asyncio.run(_fetch_cid_status_from_ipfs_async(cid))


def calculate_vote_ipfs_description(text: str) -> IPFSUploadResult:
    messages = verify_ipfs_description(text)
    calculated_cid = ""
    if not text:
        # no text provided
        return IPFSUploadResult(cid=calculated_cid, messages=messages, text=text)

    calculated_cid = calculate_cid_hash(text)
    if not calculated_cid:
        raise Exception("Couldn't calculate the ipfs hash for description.")

    return IPFSUploadResult(cid=calculated_cid, messages=messages, text=text)


def upload_vote_ipfs_description(text: str) -> IPFSUploadResult:
    messages = verify_ipfs_description(text)
    calculated_cid = ""
    if not text:
        # no text provided
        return IPFSUploadResult(cid=calculated_cid, messages=messages, text=text)
    try:
        calculated_cid = calculate_cid_hash(text)
        if not calculated_cid:
            raise Exception("Couldn't calculate the ipfs hash for description.")

        status = fetch_cid_status_from_ipfs(calculated_cid)
        if status < 400:
            # have found file so CID is good
            return IPFSUploadResult(cid=calculated_cid, messages=messages, text=text)

        uploaded_cid = _upload_str_to_ipfs(text)
        if calculated_cid == uploaded_cid:
            # uploaded has same CID
            return IPFSUploadResult(cid=calculated_cid, messages=messages, text=text)

        messages.append(
            (
                "error",
                "The calculated description CID hashsum differs from the uploaded CID. "
                f"Calculated CID is {calculated_cid}, but uploaded is {uploaded_cid}",
            )
        )
        # has two different CID
        return IPFSUploadResult(cid=calculated_cid, messages=messages, text=text)

    except Exception as err:
        messages.append(("error", f"Unexpected error during upload description process: '{str(err)}'"))
        if calculated_cid:
            messages.append(
                (
                    "error",
                    "Unable to upload the description to IPFS. "
                    f"But you could use calculated CID: {calculated_cid} and upload description later.",
                )
            )
        else:
            messages.append(
                (
                    "error",
                    (
                        "Unable to calculate the description CID or upload the description to IPFS. "
                        "Your vote will not contain IPFS description."
                    ),
                )
            )
        # exception during upload or calculation
        return IPFSUploadResult(cid=calculated_cid, messages=messages, text=text)


def get_lido_vote_cid_from_str(text: str) -> str:
    result = re.findall(REG_VOTE_CID_WITH_PREFIX_LAST, text)
    if len(result):
        return result[0]
    return ""


def make_lido_vote_cid(cid: str) -> str:
    if cid and re.search(rf"^{REG_VOTE_CID}$", cid):
        return f"{VOTE_CID_PREFIX}{cid}"
    return ""

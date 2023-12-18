import re
from os import linesep

from utils.ipfs import (
    verify_ipfs_description,
    REG_CID_DEFAULT,
    calculate_cid_hash,
    fetch_cid_status_from_ipfs,
    upload_vote_ipfs_description,
    make_lido_vote_cid,
    get_lido_vote_cid_from_str,
)


def test_verify_ipfs_description_empty():
    result = verify_ipfs_description("")
    assert len(result) == 1
    assert result[0][0] == "error"
    assert result[0][1] == (
        "You provided an empty string as description. If you provide text as a description, "
        "it will help users to make a voting decision. The description is stored on the IPFS network"
        "and take fixed space in the script regardless of text length."
    )

def test_verify_ipfs_description_good_address():
    result = verify_ipfs_description(
        f" `0xDfe76d11b365f5e0023343A367f0b311701B3bc1` "
    )
    assert len(result) == 0


def test_verify_ipfs_description_ugly_addresses():
    tail = "1234567890abcdefABCDEF00000000000000000"
    result = verify_ipfs_description(
        f"0x1{tail}` 0x2{tail}` `0x3{tail} `0x4{tail}` `0xDfe76d11b365f5e0023343A367f0b311701B3bc1` 0x5{tail}0x6{tail} 0x7{tail} `0x8{tail}"
    )
    assert len(result) == 2
    assert result[0][0] == "warning"

    warning_ids = ["0x1", "0x2", "0x3", "0x7", "0x8"]
    wallet_ids = re.findall(r"\b0x\d", result[0][1])
    assert wallet_ids == warning_ids
    wallets = list(map(lambda x: f"{x}{tail}", warning_ids))

    assert result[0][1] == (
        "You have wallet addresses in description which has no Markdown style. "
        "You could use inline code block to make it looks better. "
        "You need to add '`' before and after the address. Here is the list of addresses:\n"
        f"{linesep.join(wallets)}"
    )
    assert result[1][0] == "error"

    error_ids = ["0x1", "0x2", "0x3", "0x4", "0x7", "0x8"]
    wallet_ids = re.findall(r"\b0x\d", result[1][1])
    print(result[1][1])
    assert wallet_ids == error_ids
    wallets = list(map(lambda x: f"{x}{tail}", error_ids))

    assert result[1][1] == (
        "You have wallet addresses in description which has wrong hash sum. "
        "Here is the list of addresses:\n"
        f"{linesep.join(wallets)}"
    )


def test_verify_ipfs_description_ugly_cids():
    tail = "777777777766666666665555555555444444444433333333332222222222"
    result = verify_ipfs_description(
        f"b22{tail}` b23{tail}` `b24{tail} `b25{tail}` b26{tail}1b27{tail} b2A{tail} `b2b{tail}"
    )
    assert len(result) == 1
    assert result[0][0] == "warning"

    warning_ids = ["b22", "b23", "b24", "b2A", "b2b"]
    cid_ids = re.findall(r"\bb2[2-7a-zA_Z]", result[0][1])
    assert cid_ids == warning_ids
    cids = list(map(lambda x: f"{x}{tail}", warning_ids))

    assert result[0][1] == (
        "You have CIDs in description which has no Markdown style. "
        "You could use inline code block to make it looks better. "
        "You need to add '`' before and after CID. Here is the list of CID:\n"
        f"{linesep.join(cids)}"
    )


def test_find_cids():
    cid_list = [
        "QmRKs2ZfuwvmZA3QAWmCqrGUjV9pxtBUDP3wuc6iVGnjA2",
        "f017012202c5f688262e0ece8569aa6f94d60aad55ca8d9d83734e4a7430d0cff6588ec2b",
        "F017012202C5F688262E0ECE8569AA6F94D60AAD55CA8D9D83734E4A7430D0CFF6588EC2B",
        "BAFYBEIBML5UIEYXA5TUFNGVG7FGWBKWVLSUNTWBXGTSKOQYNBT7WLCHMFM",
        "bafybeibml5uieyxa5tufngvg7fgwbkwvlsuntwbxgtskoqynbt7wlchmfm",
        "zdj7WYR7PzjmRQNRsMKuFipiE73MhMGgRbc5hTUaQVPJiMdKx",
        "mAXASICxfaIJi4OzoVpqm+U1gqtVcqNnYNzTkp0MNDP9liOwr",
        "uAXASICxfaIJi4OzoVpqm-U1gqtVcqNnYNzTkp0MNDP9liOwr",
        "UAXASICxfaIJi4OzoVpqm-U1gqtVcqNnYNzTkp0MNDP9liOwr",
    ]

    result = re.findall(REG_CID_DEFAULT, f" {' '.join(cid_list)} ")
    assert len(result) == len(cid_list)


def test_calculate_cid_hash():
    result = calculate_cid_hash("")
    assert result == "bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku"
    result = calculate_cid_hash("test string")
    assert result == "bafkreigvk6oenx6mp4mca4at4znujzgljywcfghuvrcxxkhye5b7ghutbm"


def test_fetch_cid_status_from_ipfs():
    status = fetch_cid_status_from_ipfs("")
    assert status == 404
    status = fetch_cid_status_from_ipfs("bafkreigvk6oenx6mp4mca4at4znujzgljywcfghuvrcxxkhye5b7ghutbm")
    assert status == 200
    status = fetch_cid_status_from_ipfs("bafkreigdsodbw6dlajnk7xyudw52cutzioovt7r7mrdf3t3cx7xfzz3eou")
    assert status == 404


def test_upload_vote_ipfs_description():
    result = upload_vote_ipfs_description("test string")

    assert result["cid"] == "bafkreigvk6oenx6mp4mca4at4znujzgljywcfghuvrcxxkhye5b7ghutbm"
    assert result["text"] == "test string"
    assert len(result["messages"]) == 0

    result = upload_vote_ipfs_description("")
    assert result["cid"] == ""
    assert result["text"] == ""
    assert result["messages"][0][0] == "error"
    assert result["messages"][0][1] == (
        "You provided an empty string as description. If you provide text as a description, "
        "it will help users to make a voting decision. The description is stored on the IPFS network"
        "and take fixed space in the script regardless of text length."
    )


def test_make_lido_vote_cid():
    tail = "777777777766666666665555555555444444444433333333332222222222"
    assert make_lido_vote_cid("") == ""
    assert make_lido_vote_cid("zzz") == ""
    assert make_lido_vote_cid(f"b22{tail}") == f"lidovoteipfs://b22{tail}"


def test_get_lido_vote_cid_from_str():
    tail = "777777777766666666665555555555444444444433333333332222222222"

    assert get_lido_vote_cid_from_str("") == ""
    assert get_lido_vote_cid_from_str("lidovoteipfs://zzz") == ""
    assert get_lido_vote_cid_from_str(f"b22{tail}") == ""
    assert make_lido_vote_cid(f" b22{tail}") == ""
    assert make_lido_vote_cid(f"b22{tail} ") == ""
    assert get_lido_vote_cid_from_str(f"lidovoteipfs://b22{tail}") == f"b22{tail}"
    assert get_lido_vote_cid_from_str(f"lidovoteipfs://b22{tail}   ") == f"b22{tail}"
    assert get_lido_vote_cid_from_str(f"xlidovoteipfs://b22{tail}   ") == ""
    assert get_lido_vote_cid_from_str(f"lidovoteipfs://b23{tail} lidovoteipfs://b22{tail}   ") == f"b22{tail}"
    long_desc = """

    lidovoteipfs://b23777777777766666666665555555555444444444433333333332222222222
    lidovoteipfs://b22777777777766666666665555555555444444444433333333332222222222
    """
    assert get_lido_vote_cid_from_str(long_desc) == f"b22{tail}"

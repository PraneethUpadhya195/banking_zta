from typing import Any


def mask_account_number(account_number: str) -> str:
    if len(account_number) <= 4:
        return account_number
    return "XXXX-XXXX-" + account_number[-4:]


def apply_mask(account_data: dict, role: str) -> dict:
    if role in ("admin", "manager"):
        return account_data

    if role == "teller":
        return {
            "account_number": mask_account_number(account_data["account_number"]),
            "balance": account_data["balance"],
            "owner": account_data.get("owner")
        }

    if role == "customer":
        return {
            "account_number": mask_account_number(account_data["account_number"]),
            "balance": account_data["balance"]
        }

    return {}
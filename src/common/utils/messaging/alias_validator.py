import re
from common.enums.reserved_aliases import RESERVED_ALIASES
from exceptions.alias import AliasValidationError

ALIAS_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,32}$')


class AliasValidator:
    @staticmethod
    def validate(alias: str) -> None:
        if len(alias) < 3:
            raise AliasValidationError("Alias is too 🤏short🤏 - minimum 3 characters.")
        if len(alias) > 32:
            raise AliasValidationError("Alias is too 🌭long🌭 - maximum 32 characters.")
        if not ALIAS_PATTERN.match(alias):
            raise AliasValidationError(
                "Alias can only contain letters, digits, and underscores (_)."
            )
        if alias.lower() in RESERVED_ALIASES:
            raise AliasValidationError(
                f"<code>{alias}</code> is a reserved name and cannot be used as an alias 🥀"
            )

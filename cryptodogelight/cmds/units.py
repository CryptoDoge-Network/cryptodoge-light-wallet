from typing import Dict

# The rest of the codebase uses mojos everywhere.
# Only use these units for user facing interfaces.
units: Dict[str, int] = {
    "cryptodogelight": 10 **  6,  # 1 cryptodogelight (XCD) is 1,000,000 mojo (1 million)
    "mojo": 1,
    "colouredcoin": 10 ** 3,  # 1 coloured coin is 1000 colouredcoin mojos
}

# wallet_test.py

from core.wallet import Wallet

# -----------------------------------
# CREATE WALLET
# -----------------------------------

result = Wallet.create_with_seed()

wallet = result["wallet"]

seed_phrase = result["seed_phrase"]

print("\n==============================")
print(" NEW NETHERA WALLET CREATED ")
print("==============================\n")

print("SEED PHRASE:\n")
print(seed_phrase)

print("\nADDRESS:\n")
print(wallet.get_address())

print("\nPUBLIC KEY:\n")
print(wallet.get_public_key())

print("\nPRIVATE KEY:\n")
print(wallet.get_private_key())

# -----------------------------------
# EXPORT BACKUP
# -----------------------------------

backup_path = wallet.export_backup(
    seed_phrase
)

print("\nBACKUP SAVED:")
print(backup_path)

# -----------------------------------
# RESTORE FROM SEED
# -----------------------------------

restored_wallet = (
    Wallet.from_seed_phrase(
        seed_phrase
    )
)

print("\n==============================")
print(" RESTORED WALLET ")
print("==============================\n")

print(
    "RESTORED ADDRESS:\n"
)

print(
    restored_wallet.get_address()
)

print("\nMATCH CHECK:\n")

print(
    wallet.get_address()
    ==
    restored_wallet.get_address()
)

# -----------------------------------
# CREATE SIGNED TX
# -----------------------------------

print("\n==============================")
print(" SIGNED TRANSACTION ")
print("==============================\n")

tx = wallet.create_signed_transaction(
    receiver="bob",
    amount=25,
    fee=0.1
)

print(tx)

# -----------------------------------
# VERIFY TX
# -----------------------------------

verified = Wallet.verify_transaction(

    {
        "sender": tx["sender"],
        "receiver": tx["receiver"],
        "amount": tx["amount"],
        "fee": tx["fee"],
        "timestamp": tx["timestamp"]
    },

    tx["signature"],

    tx["public_key"]
)

print("\nTX VERIFIED:\n")
print(verified)

# -----------------------------------
# IMPORT BACKUP FILE
# -----------------------------------

imported_wallet = (
    Wallet.import_wallet(
        backup_path
    )
)

print("\n==============================")
print(" IMPORTED WALLET ")
print("==============================\n")

print(
    imported_wallet.get_address()
)

print("\nIMPORT MATCH:\n")

print(
    imported_wallet.get_address()
    ==
    wallet.get_address()
)

print("\n==============================")
print(" TEST COMPLETE ")
print("==============================\n")

import os
from cryptography.fernet import Fernet

encrypt_key = os.getenv("encrypt_key")

def encrypt_decrypt_string(input_string: str, mode: str) -> str:
    """Encrypts or decrypts a string with a key from environment variables.

    Args:
        input_string (str): The string to encrypt or decrypt.
        mode (str): 'encrypt' to encrypt the string, 'decrypt' to decrypt it.

    Returns:
        str: The encrypted or decrypted string.

    Raises:
        ValueError: If the mode is invalid or encryption key is missing.
    """
    if not encrypt_key:
        raise ValueError("Encryption key not set in environment variables")

    fernet = Fernet(encrypt_key.encode())

    if mode == "encrypt":
        encrypted = fernet.encrypt(input_string.encode())
        return encrypted.decode()

    elif mode == "decrypt":
        decrypted = fernet.decrypt(input_string.encode())
        return decrypted.decode()

    else:
        raise ValueError("Mode must be either 'encrypt' or 'decrypt'")

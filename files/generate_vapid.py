from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

private_key = ec.generate_private_key(ec.SECP256R1())
private_key_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
public_key = private_key.public_key()
public_key_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

print("VAPID_PRIVATE_KEY (PEM):")
print(private_key_bytes.decode())
print()
print("VAPID_PRIVATE_KEY (b64):")
print(b64url(private_key_bytes))
print()
print("VAPID_PUBLIC_KEY (b64):")
print(b64url(public_key_bytes))

# Precompute the CRC32c (Castagnoli) table
CRC32C_TABLE: list[int] = []
for i in range(256):
    crc = i
    for _ in range(8):
        if crc & 1:
            crc: int = (crc >> 1) ^ 0x82F63B78
        else:
            crc >>= 1
    CRC32C_TABLE.append(crc)


def crc32c(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc = (crc >> 8) ^ CRC32C_TABLE[(crc ^ byte) & 0xFF]
    return crc ^ 0xFFFFFFFF

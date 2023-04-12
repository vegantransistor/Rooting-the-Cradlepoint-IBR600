from pathlib import Path

miso_file = Path("rootfs_miso.bin")
mosi_file = Path("rootfs_mosi.bin")
rootfs_file = Path("rootfs.bin")

try:
    with miso_file.open(mode="rb") as miso:
        rootfsmiso = miso.read()
    with mosi_file.open(mode="rb") as mosi:
        rootfsmosi = mosi.read()    
except OSError as error:
    print(f"Could not read miso/mosi files: {error}")

rootfs = bytearray(len(rootfsmosi))

index_spi = 0
index_data = 0

while index_spi < len(rootfsmosi):
    if rootfsmosi[index_spi] == int('0x13',16):
        index_spi = index_spi + 4
    elif rootfsmosi[index_spi] == int('0x03',16):
        index_spi = index_spi + 4
    elif rootfsmosi[index_spi] == int('0x0f',16):
        index_spi = index_spi + 3
    else:
        rootfs[index_data]= rootfsmiso[index_spi]
        index_spi = index_spi + 1
        index_data = index_data + 1

print(index_spi)
print(index_data)

rootfsresized = rootfs[0:index_data]

try:
    with rootfs_file.open(mode="wb") as rootfs:
        rootfs.write(rootfsresized)
except OSError as error:
    print(f"Could not write to rootfs: {error}")



miso = open("rootfs_miso.bin", mode="rb")
mosi = open("rootfs_mosi.bin", mode="rb")

rootfsmiso = miso.read()
rootfsmosi = mosi.read()

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

root = open("rootfs.bin", mode="wb")
root.write(rootfsresized)

import bitjws


def create_username_address():
    privkey = bitjws.PrivateKey()
    my_pubkey = privkey.pubkey.serialize()
    my_address = bitjws.pubkey_to_addr(my_pubkey)
    username = str(my_address)[0:8]
    return username, my_address

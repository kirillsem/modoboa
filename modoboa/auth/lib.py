# coding: utf-8
from Crypto.Cipher import AES
import base64
import random
import string
from modoboa.lib import parameters


def random_key(l=16):
    """Generate a random key

    :param integer l: the key's length
    :return: a string
    """
    char_set = string.digits + string.letters + string.punctuation
    return ''.join(random.sample(char_set * l, l))


def encrypt(clear):
    key = parameters.get_admin("SECRET_KEY", app="admin")
    obj = AES.new(key, AES.MODE_ECB)
    if type(clear) is unicode:
        clear = clear.encode("utf-8")
    if len(clear) % AES.block_size:
        clear += " " * (AES.block_size - len(clear) % AES.block_size)
    ciph = obj.encrypt(clear)
    ciph = base64.b64encode(ciph)
    return ciph


def decrypt(ciph):
    obj = AES.new(
        parameters.get_admin("SECRET_KEY", app="admin"), AES.MODE_ECB
    )
    ciph = base64.b64decode(ciph)
    clear = obj.decrypt(ciph)
    return clear.rstrip(' ')


def get_password(request):
    return decrypt(request.session["password"])

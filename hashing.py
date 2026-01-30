import time


# =====================================================
# SIMPLE CSPRNG (XORSHIFT) - Educational
# =====================================================

class RNG:
    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFFFFFFFFFF

    def next(self):
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 7)
        x ^= (x << 17) & 0xFFFFFFFFFFFFFFFF
        self.state = x
        return x

    def token(self, n=32):
        out = ""
        for _ in range(n):
            out += hex(self.next() & 0xF)[2:]
        return out


# =====================================================
# SHA-256 IMPLEMENTATION (FROM SCRATCH)
# =====================================================

K = [
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,
    0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,
    0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,
    0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,
    0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,
    0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,
    0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,
    0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,
    0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,
    0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,
    0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,
    0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
]


def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


def sha256(data):

    if isinstance(data, str):
        data = data.encode()

    h = [
        0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
        0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
    ]

    length = len(data) * 8
    data += b"\x80"

    while (len(data) * 8) % 512 != 448:
        data += b"\x00"

    data += length.to_bytes(8, "big")

    for i in range(0, len(data), 64):

        chunk = data[i:i+64]
        w = []

        for j in range(16):
            w.append(int.from_bytes(chunk[j*4:j*4+4], "big"))

        for j in range(16, 64):
            s0 = rotr(w[j-15],7) ^ rotr(w[j-15],18) ^ (w[j-15]>>3)
            s1 = rotr(w[j-2],17) ^ rotr(w[j-2],19) ^ (w[j-2]>>10)
            w.append((w[j-16]+s0+w[j-7]+s1)&0xFFFFFFFF)

        a,b,c,d,e,f,g,hv = h

        for j in range(64):

            S1 = rotr(e,6)^rotr(e,11)^rotr(e,25)
            ch = (e&f) ^ (~e&g)
            temp1 = (hv+S1+ch+K[j]+w[j])&0xFFFFFFFF
            S0 = rotr(a,2)^rotr(a,13)^rotr(a,22)
            maj = (a&b)^(a&c)^(b&c)
            temp2 = (S0+maj)&0xFFFFFFFF

            hv=g
            g=f
            f=e
            e=(d+temp1)&0xFFFFFFFF
            d=c
            c=b
            b=a
            a=(temp1+temp2)&0xFFFFFFFF

        h = [
            (h[0]+a)&0xFFFFFFFF,
            (h[1]+b)&0xFFFFFFFF,
            (h[2]+c)&0xFFFFFFFF,
            (h[3]+d)&0xFFFFFFFF,
            (h[4]+e)&0xFFFFFFFF,
            (h[5]+f)&0xFFFFFFFF,
            (h[6]+g)&0xFFFFFFFF,
            (h[7]+hv)&0xFFFFFFFF
        ]

    return "".join(f"{x:08x}" for x in h)


# =====================================================
# HMAC (FROM SCRATCH)
# =====================================================

def hmac_sha256(key, msg):

    if isinstance(key,str):
        key = key.encode()
    if isinstance(msg,str):
        msg = msg.encode()

    block = 64

    if len(key) > block:
        key = bytes.fromhex(sha256(key))

    key = key.ljust(block, b"\x00")

    o = bytes(k ^ 0x5c for k in key)
    i = bytes(k ^ 0x36 for k in key)

    return sha256(o + bytes.fromhex(sha256(i + msg)))


# =====================================================
# OTP SYSTEM
# =====================================================

DB = {}


def make_token(secret, user, rng):

    exp = int(time.time()) + 300

    rand = rng.token(32)

    token = f"{user}:{exp}:{rand}"

    h = hmac_sha256(secret, token)

    DB[user] = {
        "hash": h,
        "exp": exp
    }

    return token


def verify(secret, user, token):

    if user not in DB:
        return False

    rec = DB[user]

    if time.time() > rec["exp"]:
        del DB[user]
        return False

    h = hmac_sha256(secret, token)

    if h != rec["hash"]:
        return False

    del DB[user]
    return True


# =====================================================
# MAIN
# =====================================================

def main():

    print("\n=== PURE PYTHON OTP SYSTEM ===\n")

    secret = input("Server secret: ")
    user = input("Email/Phone: ")

    seed = int(time.time()*1000000)
    rng = RNG(seed)

    token = make_token(secret, user, rng)

    print("\nGenerated OTP:")
    print(token)

    print("\n(Only hash stored)")
    print(DB[user]["hash"])

    entered = input("\nEnter OTP: ")

    if verify(secret, user, entered):
        print("\n✅ Login OK")
    else:
        print("\n❌ Invalid")


if __name__ == "__main__":
    main()
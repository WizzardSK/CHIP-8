# c8shot.py <rom> <title.png> <snap.png>
# A small CHIP-8 / SUPER-CHIP interpreter that runs a program without a
# player and saves two frames: the first with something drawn on it (title)
# and one a few seconds later (snap). When the program waits for a key, a
# key is pressed for it after a while, so menus and "press a key" screens
# move on.
import sys, random
from PIL import Image

FONT = [0xF0,0x90,0x90,0x90,0xF0, 0x20,0x60,0x20,0x20,0x70, 0xF0,0x10,0xF0,0x80,0xF0, 0xF0,0x10,0xF0,0x10,0xF0,
        0x90,0x90,0xF0,0x10,0x10, 0xF0,0x80,0xF0,0x10,0xF0, 0xF0,0x80,0xF0,0x90,0xF0, 0xF0,0x10,0x20,0x40,0x40,
        0xF0,0x90,0xF0,0x90,0xF0, 0xF0,0x90,0xF0,0x10,0xF0, 0xF0,0x90,0xF0,0x90,0x90, 0xE0,0x90,0xE0,0x90,0xE0,
        0xF0,0x80,0x80,0x80,0xF0, 0xE0,0x90,0x90,0x90,0xE0, 0xF0,0x80,0xF0,0x80,0xF0, 0xF0,0x80,0xF0,0x80,0x80]
BIG = [0x3C,0x7E,0xE7,0xC3,0xC3,0xC3,0xC3,0xE7,0x7E,0x3C, 0x18,0x38,0x58,0x18,0x18,0x18,0x18,0x18,0x18,0x3C,
       0x3E,0x7F,0xC3,0x06,0x0C,0x18,0x30,0x60,0xFF,0xFF, 0x3C,0x7E,0xC3,0x03,0x0E,0x0E,0x03,0xC3,0x7E,0x3C,
       0x06,0x0E,0x1E,0x36,0x66,0xC6,0xFF,0xFF,0x06,0x06, 0xFF,0xFF,0xC0,0xC0,0xFC,0xFE,0x03,0xC3,0x7E,0x3C,
       0x3E,0x7C,0xE0,0xC0,0xFC,0xFE,0xC3,0xC3,0x7E,0x3C, 0xFF,0xFF,0x03,0x06,0x0C,0x18,0x30,0x60,0x60,0x60,
       0x3C,0x7E,0xC3,0xC3,0x7E,0x7E,0xC3,0xC3,0x7E,0x3C, 0x3C,0x7E,0xC3,0xC3,0x7F,0x3F,0x03,0x03,0x3E,0x7C]

class VM:
    def __init__(self, rom):
        self.m = bytearray(4096); self.m[0x50:0x50+80] = bytes(FONT); self.m[0xA0:0xA0+100] = bytes(BIG)
        self.m[0x200:0x200+len(rom)] = rom
        self.v = [0]*16; self.i = 0; self.pc = 0x200; self.sp = []; self.dt = 0; self.st = 0
        self.hi = False; self.w, self.h = 64, 32; self.fb = [[0]*128 for _ in range(64)]
        self.keys = [0]*16; self.wait = None; self.waited = 0; self.flags = [0]*16; self.halted = False
        self.drawn = False
    def clear(self):
        for r in self.fb: r[:] = [0]*128
    def draw(self, x, y, n):
        self.v[15] = 0; self.drawn = True
        w = 16 if (n == 0 and self.hi) else 8; rows = 16 if n == 0 else n
        x %= self.w; y %= self.h
        for r in range(rows):
            if w == 16: bits = (self.m[(self.i + r*2) & 0xFFF] << 8) | self.m[(self.i + r*2 + 1) & 0xFFF]
            else: bits = self.m[(self.i + r) & 0xFFF]
            yy = y + r
            if yy >= self.h: break
            for c in range(w):
                if bits & (1 << (w - 1 - c)):
                    xx = x + c
                    if xx >= self.w: break
                    if self.fb[yy][xx]: self.v[15] = 1
                    self.fb[yy][xx] ^= 1
    def step(self):
        if self.halted: return
        if self.wait is not None:
            self.waited += 1
            if self.waited > 400:  # about a second of waiting: press a key
                k = random.choice([5, 6, 4, 0xA, 1, 2, 8])
                self.v[self.wait] = k; self.wait = None; self.waited = 0
            return
        op = (self.m[self.pc & 0xFFF] << 8) | self.m[(self.pc + 1) & 0xFFF]; self.pc = (self.pc + 2) & 0xFFF
        x = (op >> 8) & 15; y = (op >> 4) & 15; n = op & 15; nn = op & 0xFF; nnn = op & 0xFFF; v = self.v
        t = op >> 12
        if op == 0x00E0: self.clear()
        elif op == 0x00EE: self.pc = self.sp.pop() if self.sp else self.pc
        elif op & 0xFFF0 == 0x00C0:
            for _ in range(n): self.fb.insert(0, [0]*128); self.fb.pop()
        elif op == 0x00FB:
            for r in self.fb: r[:] = [0]*4 + r[:124]
        elif op == 0x00FC:
            for r in self.fb: r[:] = r[4:] + [0]*4
        elif op == 0x00FD: self.halted = True
        elif op == 0x00FE: self.hi = False; self.w, self.h = 64, 32; self.clear()
        elif op == 0x00FF: self.hi = True; self.w, self.h = 128, 64; self.clear()
        elif t == 0: pass
        elif t == 1:
            if nnn == self.pc - 2: self.halted = True
            self.pc = nnn
        elif t == 2: self.sp.append(self.pc); self.pc = nnn
        elif t == 3:
            if v[x] == nn: self.pc += 2
        elif t == 4:
            if v[x] != nn: self.pc += 2
        elif t == 5:
            if v[x] == v[y]: self.pc += 2
        elif t == 6: v[x] = nn
        elif t == 7: v[x] = (v[x] + nn) & 0xFF
        elif t == 8:
            if n == 0: v[x] = v[y]
            elif n == 1: v[x] |= v[y]
            elif n == 2: v[x] &= v[y]
            elif n == 3: v[x] ^= v[y]
            elif n == 4: s = v[x] + v[y]; v[x] = s & 0xFF; v[15] = 1 if s > 255 else 0
            elif n == 5: f = 1 if v[x] >= v[y] else 0; v[x] = (v[x] - v[y]) & 0xFF; v[15] = f
            elif n == 6: f = v[x] & 1; v[x] >>= 1; v[15] = f
            elif n == 7: f = 1 if v[y] >= v[x] else 0; v[x] = (v[y] - v[x]) & 0xFF; v[15] = f
            elif n == 0xE: f = v[x] >> 7; v[x] = (v[x] << 1) & 0xFF; v[15] = f
        elif t == 9:
            if v[x] != v[y]: self.pc += 2
        elif t == 0xA: self.i = nnn
        elif t == 0xB: self.pc = (nnn + v[0]) & 0xFFF
        elif t == 0xC: v[x] = random.randint(0, 255) & nn
        elif t == 0xD: self.draw(v[x], v[y], n)
        elif t == 0xE:
            if nn == 0x9E and self.keys[v[x] & 15]: self.pc += 2
            elif nn == 0xA1 and not self.keys[v[x] & 15]: self.pc += 2
        elif t == 0xF:
            if nn == 0x07: v[x] = self.dt
            elif nn == 0x0A: self.wait = x
            elif nn == 0x15: self.dt = v[x]
            elif nn == 0x18: self.st = v[x]
            elif nn == 0x1E: self.i = (self.i + v[x]) & 0xFFF
            elif nn == 0x29: self.i = 0x50 + (v[x] & 15) * 5
            elif nn == 0x30: self.i = 0xA0 + (v[x] & 15) * 10
            elif nn == 0x33: self.m[self.i] = v[x] // 100; self.m[self.i+1] = v[x] // 10 % 10; self.m[self.i+2] = v[x] % 10
            elif nn == 0x55:
                for k in range(x + 1): self.m[(self.i + k) & 0xFFF] = v[k]
            elif nn == 0x65:
                for k in range(x + 1): v[k] = self.m[(self.i + k) & 0xFFF]
            elif nn == 0x75: self.flags[:x+1] = v[:x+1]
            elif nn == 0x85: v[:x+1] = self.flags[:x+1]
    def frame(self, ips=12):
        for _ in range(ips): self.step()
        if self.dt: self.dt -= 1
        if self.st: self.st -= 1
    def lit(self):
        return sum(sum(r[:self.w]) for r in self.fb[:self.h])
    def image(self):
        img = Image.new('RGB', (self.w, self.h), (0, 0, 0)); px = img.load()
        for yy in range(self.h):
            for xx in range(self.w):
                if self.fb[yy][xx]: px[xx, yy] = (255, 255, 255)
        s = 10 if self.w == 64 else 5
        return img.resize((self.w * s, self.h * s), Image.NEAREST)

def main():
    random.seed(1)
    rom = open(sys.argv[1], 'rb').read()
    vm = VM(rom)
    title = None; snap = None
    # input: some games only move on with a key held, so a key is held down
    # now and then, the ones games use most (2 4 5 6 8 for moving, 1 4 for pong)
    for f in range(60 * 30):
        if f % 90 == 45: vm.keys[random.choice([5, 4, 6, 1, 2, 8, 0xC])] = 1
        if f % 90 == 60: vm.keys = [0]*16
        vm.frame()
        if vm.lit() > 8:
            if title is None and f > 20: title = vm.image()
            if f > 60 * 6 and snap is None: snap = vm.image()
        if vm.halted and title is not None:
            break
    last = vm.image() if vm.lit() > 8 else None
    snap = snap or last or title
    if title is None: title = snap
    if title is None: sys.exit(1)
    title.save(sys.argv[2]); snap.save(sys.argv[3])

main()

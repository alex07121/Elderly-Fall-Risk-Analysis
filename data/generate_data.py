#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fall Risk Prediction Data Generator (2000 rows) — v2
遵循 new_IA_Part1.docx 蓝图规格（分布 + 示例用例 + 相关性约束）
"""
import os
import random
import statistics as st

_DATA_DIR = os.path.dirname(os.path.abspath(__file__))

random.seed(42)
N = 2000

def clip(x, lo, hi):
    return max(lo, min(hi, x))

def rank_correlate(x, y, rho):
    """重排 y 使与 x 的秩相关 ≈ rho，且 y 边缘分布不变"""
    n = len(x)
    x_sorted_idx = sorted(range(n), key=lambda i: x[i])
    rank_x = [0] * n
    for r, idx in enumerate(x_sorted_idx):
        rank_x[idx] = r
    target_rank = [rho * r + (1 - rho) * random.uniform(0, n - 1) for r in rank_x]
    order = sorted(range(n), key=lambda i: target_rank[i])
    y_sorted = sorted(y)
    y_new = [0.0] * n
    for r, idx in enumerate(order):
        y_new[idx] = y_sorted[r]
    return y_new

# ---------- 1. age: N(79.1, 7.0), [60,100] ----------
ages = [clip(round(random.gauss(79.1, 7.0)), 60, 100) for _ in range(N)]

# ---------- 1.5 sex: F 57% / M 43%（养老机构老年女性偏多） ----------
sex = ['F' if random.random() < 0.57 else 'M' for _ in range(N)]

# ---------- 2. high_risk_medication: Bernoulli 54.4% ----------
hr_med = [random.random() < 0.544 for _ in range(N)]

# ---------- 3. cognitive_impairment: 0/1/2, age 正相关 ----------
cog = []
for i in range(N):
    a = ages[i]
    p2 = clip(0.225 + (a - 79.1) / 100.0 * 0.35, 0.10, 0.42)
    p1 = clip(0.325 + (a - 79.1) / 100.0 * 0.05, 0.22, 0.40)
    p0 = 1.0 - p1 - p2
    r = random.random()
    if r < p0:
        cog.append(0)
    elif r < p0 + p1:
        cog.append(1)
    else:
        cog.append(2)

# ---------- 4. polypharmacy_count: 均值4.55, 与 med 正相关(r~0.4), age 正相关 ----------
poly = []
for i in range(N):
    base = random.gauss(4.1, 2.6)
    if hr_med[i]:
        base += 1.4
    else:
        base -= 1.1
    if ages[i] >= 85:
        base += 0.3
    poly.append(clip(round(base), 0, 15))

# ---------- 5. orthostatic_hypotension: 33.7%, med/age/poly 正相关 ----------
ortho = []
for i in range(N):
    p = 0.245
    if hr_med[i]:
        p += 0.13
    if ages[i] >= 85:
        p += 0.04
    if poly[i] >= 5:
        p += 0.03
    ortho.append(random.random() < clip(p, 0, 0.85))

# ---------- 6. night_bed_exits: 右偏离散, 认知障碍右尾更长 ----------
def draw_night_bed_exits(c):
    if c == 0:
        probs = [0.235, 0.26, 0.23]          # 0,1,2
        tail = [0.145, 0.09, 0.04, 0.018, 0.005, 0.002]  # 3..8
    else:
        probs = [0.15, 0.21, 0.20]
        tail = [0.17, 0.12, 0.075, 0.04, 0.02, 0.015]
    total = sum(probs) + sum(tail)
    r = random.random() * total
    acc = 0.0
    for k, p in enumerate(probs):
        acc += p
        if r < acc:
            return k
    for k, p in enumerate(tail, start=3):
        acc += p
        if r < acc:
            return k
    return 8

nb = [draw_night_bed_exits(cog[i]) for i in range(N)]

# ---------- 7. night_activity_duration_min: 右偏, median~28 mean~34, 与 nb 强正相关(r~0.8) ----------
nd_raw = [clip(random.gammavariate(1.89, 18.0), 0.0, 120.0) for _ in range(N)]
nd = [round(v, 1) for v in rank_correlate(nb, nd_raw, 0.68)]

# ---------- 8. tug_seconds: 轻度右偏, mean~15.2 median~15, [8,31.9] ----------
tug = []
for i in range(N):
    a = ages[i]
    age_shift = (a - 79.1) / 7.0 * 1.6
    v = random.gauss(14.35 + age_shift, 4.9)
    if random.random() < 0.13:
        v += random.expovariate(1.0 / 4.0)   # 右尾
    tug.append(clip(round(v, 1), 8.0, 31.9))

# ---------- 9. mobility_score: 严格由 TUG 映射 ----------
mob = []
for i in range(N):
    t = tug[i]
    if t < 13.5:
        mob.append(random.choices([8, 9, 10], weights=[0.45, 0.35, 0.20], k=1)[0])
    elif t <= 20.0:
        mob.append(random.choices([5, 6, 7], weights=[0.20, 0.40, 0.40], k=1)[0])
    else:
        mob.append(random.choices([1, 2, 3, 4], weights=[0.15, 0.20, 0.35, 0.30], k=1)[0])

# ---------- 10. past_falls: 零膨胀, 0:65.2% 1:26.0% >=2:8.9% ----------
pf = []
for i in range(N):
    p0 = 0.658
    p1 = 0.260
    if ages[i] >= 85:
        p0 -= 0.03
    if tug[i] > 20:
        p0 -= 0.04
    p0 = clip(p0, 0, 1)
    r = random.random()
    if r < p0:
        pf.append(0)
    elif r < p0 + p1:
        pf.append(1)
    else:
        pf.append(random.choices([2, 3, 4, 5], weights=[0.62, 0.24, 0.10, 0.04], k=1)[0])

# ---------- 输出: fall_risk_score ----------
def raw_risk(i):
    s = 0.0
    s += 0.10 * (ages[i] - 79.1) / 7.0
    s += 0.35 * min(pf[i], 3) / 3.0
    s += 0.28 * (tug[i] - 15.2) / 5.0
    s += 0.22 * (cog[i] / 2.0)
    s += 0.16 * (1.0 if hr_med[i] else 0.0)
    s += 0.14 * min(poly[i], 10) / 10.0
    s += 0.12 * (1.0 if ortho[i] else 0.0)
    s += 0.10 * (0.5 * nb[i] / 8.0 + 0.5 * nd[i] / 120.0)
    return s

raw = [raw_risk(i) + random.gauss(0, 0.06) for i in range(N)]
mu = st.mean(raw)
sd = st.pstdev(raw)
scores = [clip(0.528 + 0.202 * (r - mu) / sd, 0.0, 1.0) for r in raw]

order = sorted(range(N), key=lambda i: scores[i])
n_low = round(N * 0.172)
n_high = round(N * 0.262)
levels = [''] * N
for idx in order[:n_low]:
    levels[idx] = 'LOW'
for idx in order[n_low:N - n_high]:
    levels[idx] = 'MEDIUM'
for idx in order[N - n_high:]:
    levels[idx] = 'HIGH'

import csv
cols = ['patient_id', 'sex', 'age', 'night_bed_exits', 'night_activity_duration_min',
        'past_falls', 'mobility_score', 'high_risk_medication', 'cognitive_impairment',
        'polypharmacy_count', 'orthostatic_hypotension', 'tug_seconds',
        'fall_risk_score', 'fall_risk_level']

with open(os.path.join(_DATA_DIR, 'fall_risk_patients_2000_v2.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(cols)
    for i in range(N):
        w.writerow([
            f'P2026{i:05d}', sex[i], ages[i], nb[i], nd[i],
            pf[i], mob[i], hr_med[i], cog[i], poly[i], ortho[i], tug[i],
            round(scores[i], 3), levels[i]
        ])

print('done, N =', N)

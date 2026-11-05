/*
 * 呼吸花园 · 提示音试听生成器
 *
 * 四种「乐器」都用手工泛音列 + 各自衰减 + 简易混响合成：
 *   handpan  手碟：基频 + 八度 + 十二度 + 高次泛音，长余音
 *   kalimba  卡林巴：明亮、短促、带一点金属拨片感
 *   marimba  马林巴：木质、温暖、衰减快
 *   bowl     颂钵：金属长音、缓慢起音、轻微拍频
 *
 * 每个 WAV 里依次是：
 *   吸气（上行 C4-G4-C5）→ 屏息（C5+G5）→ 呼气（下行 C5-G4-C4）
 *   → 空屏（低音 C3+G3）→ 开花（C6-D6-G6）→ 收束（C 大调琶音）
 *
 * 运行：node generate.js
 */
const fs = require('fs');
const path = require('path');

const SR = 32000;
const DUR = 20.0;
const OUT = __dirname;

/* ── 乐器模型 ─────────────────────────────────────────────── */
const INSTRUMENTS = {
  handpan: {
    // 手碟：基频、八度、十二度（2.71）、两个高次泛音
    partials: [
      { ratio: 1.000, amp: 1.00, tau: 3.2 },
      { ratio: 2.000, amp: 0.32, tau: 2.3 },
      { ratio: 2.710, amp: 0.20, tau: 1.6 },
      { ratio: 4.050, amp: 0.09, tau: 0.95 },
      { ratio: 5.430, amp: 0.045, tau: 0.62 },
    ],
    attack: 0.008,
    transient: 0.050,
    cutoff: 4200,
    duration: 4.2,
  },
  kalimba: {
    partials: [
      { ratio: 1.000, amp: 1.00, tau: 1.55 },
      { ratio: 2.000, amp: 0.27, tau: 1.10 },
      { ratio: 3.000, amp: 0.13, tau: 0.78 },
      { ratio: 4.200, amp: 0.065, tau: 0.50 },
      { ratio: 5.400, amp: 0.032, tau: 0.34 },
    ],
    attack: 0.0025,
    transient: 0.040,
    cutoff: 6800,
    duration: 2.8,
  },
  marimba: {
    // 马林巴琴键的模态：1 : 3.93 : 9.2
    partials: [
      { ratio: 1.000, amp: 1.00, tau: 1.15 },
      { ratio: 3.930, amp: 0.30, tau: 0.52 },
      { ratio: 9.200, amp: 0.06, tau: 0.20 },
    ],
    attack: 0.003,
    transient: 0.035,
    cutoff: 3300,
    duration: 2.2,
  },
  bowl: {
    // 颂钵：非谐泛音 + 轻微失谐，产生缓慢拍频
    partials: [
      { ratio: 1.000, amp: 1.00, tau: 5.0 },
      { ratio: 2.710, amp: 0.34, tau: 4.2 },
      { ratio: 5.180, amp: 0.15, tau: 3.2 },
      { ratio: 8.050, amp: 0.055, tau: 2.0 },
    ],
    attack: 0.055,
    transient: 0.012,
    cutoff: 5200,
    duration: 5.5,
  },
};

/* 单个音：指数衰减的正弦分音叠加，末尾做线性淡出防爆音 */
function renderNote(model, freq, vel) {
  const dur = model.duration;
  const n = Math.floor(dur * SR);
  const out = new Float32Array(n);
  const a = model.attack;

  for (const p of model.partials) {
    // 颂钵的第二个分音轻微失谐，形成拍频；其他乐器保持纯音程
    const detune = model === INSTRUMENTS.bowl && p.ratio > 2 ? 1.0022 : 1.0;
    const f = freq * p.ratio * detune;
    if (f > SR * 0.45) continue;
    const step = 2 * Math.PI * f / SR;
    let ph = 0;
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      const env = Math.min(1, t / a) * Math.exp(-t / p.tau);
      if (env < 1e-5 && t > a) break;
      out[i] += p.amp * env * Math.sin(ph);
      ph += step;
    }
  }

  // 槌头 / 拨片的极短噪声瞬态
  if (model.transient > 0) {
    const tn = Math.min(n, Math.floor(0.03 * SR));
    for (let i = 0; i < tn; i++) {
      const t = i / SR;
      out[i] += model.transient * (Math.random() * 2 - 1) * Math.exp(-t / 0.004);
    }
  }

  // 一阶低通，削掉刺耳的高频
  const alpha = 1 - Math.exp(-2 * Math.PI * model.cutoff / SR);
  let lp = 0;
  for (let i = 0; i < n; i++) {
    lp += alpha * (out[i] - lp);
    out[i] = lp * vel;
  }

  // 尾部 40ms 淡出
  const fade = Math.min(n, Math.floor(0.04 * SR));
  for (let i = 0; i < fade; i++) out[n - 1 - i] *= i / fade;
  return out;
}

function addNote(dest, model, freq, at, vel) {
  const note = renderNote(model, freq, vel);
  const offset = Math.floor(at * SR);
  const end = Math.min(dest.length, offset + note.length);
  for (let i = offset; i < end; i++) dest[i] += note[i - offset];
}

/* ── 一段完整演示 ─────────────────────────────────────────── */
const C4 = 261.63, G4 = 392.00, C5 = 523.25, G5 = 783.99;
const C3 = 130.81, G3 = 196.00;
const C6 = 1046.50, D6 = 1174.66, G6 = 1567.98;
const E4 = 329.63;

function renderDemo(model) {
  const n = Math.floor(DUR * SR);
  const dry = new Float32Array(n);

  // 吸气：上行 C4 - G4 - C5
  addNote(dry, model, C4, 0.00, 0.72);
  addNote(dry, model, G4, 0.20, 0.84);
  addNote(dry, model, C5, 0.40, 1.00);

  // 屏息：C5 + G5 纯五度
  addNote(dry, model, C5, 2.30, 0.66);
  addNote(dry, model, G5, 2.30, 0.52);

  // 呼气：下行 C5 - G4 - C4
  addNote(dry, model, C5, 5.30, 1.00);
  addNote(dry, model, G4, 5.50, 0.84);
  addNote(dry, model, C4, 5.70, 0.72);

  // 空屏：低音 C3 + G3
  addNote(dry, model, C3, 8.30, 0.58);
  addNote(dry, model, G3, 8.30, 0.46);

  // 开花：三连音 C6 - D6 - G6，很轻
  addNote(dry, model, C6, 10.80, 0.34);
  addNote(dry, model, D6, 10.96, 0.30);
  addNote(dry, model, G6, 11.12, 0.26);

  // 收束：C 大调琶音
  addNote(dry, model, C4, 12.40, 0.62);
  addNote(dry, model, E4, 12.58, 0.56);
  addNote(dry, model, G4, 12.76, 0.52);
  addNote(dry, model, C5, 12.94, 0.58);

  return reverb(dry, 0.34);
}

/* ── 简易 Schroeder 混响：4 梳状 + 2 全通 ────────────────── */
function reverb(input, wet) {
  const combDelays = [0.0297, 0.0371, 0.0411, 0.0437];
  const apDelays = [0.0050, 0.0017];
  const combs = combDelays.map(d => ({
    buf: new Float32Array(Math.floor(d * SR)), idx: 0, lp: 0,
  }));
  const aps = apDelays.map(d => ({
    buf: new Float32Array(Math.floor(d * SR)), idx: 0,
  }));
  const out = new Float32Array(input.length);
  const feedback = 0.80, damp = 0.28, apGain = 0.68;

  for (let i = 0; i < input.length; i++) {
    const x = input[i];
    let y = 0;
    for (const c of combs) {
      const b = c.buf[c.idx];
      c.lp = b * (1 - damp) + c.lp * damp;
      c.buf[c.idx] = x + c.lp * feedback;
      c.idx = (c.idx + 1) % c.buf.length;
      y += b;
    }
    y *= 0.25;
    for (const a of aps) {
      const b = a.buf[a.idx];
      const v = -apGain * y + b;
      a.buf[a.idx] = y + apGain * v;
      a.idx = (a.idx + 1) % a.buf.length;
      y = v;
    }
    out[i] = input[i] * (1 - wet) + y * wet * 1.7;
  }
  return out;
}

/* ── 归一化 + 写 WAV ─────────────────────────────────────── */
function normalize(buf, peak) {
  let max = 0;
  for (let i = 0; i < buf.length; i++) max = Math.max(max, Math.abs(buf[i]));
  if (max < 1e-9) return buf;
  const k = peak / max;
  for (let i = 0; i < buf.length; i++) buf[i] *= k;
  return buf;
}

function writeWav(file, samples) {
  const n = samples.length;
  const head = Buffer.alloc(44);
  head.write('RIFF', 0);
  head.writeUInt32LE(36 + n * 2, 4);
  head.write('WAVE', 8);
  head.write('fmt ', 12);
  head.writeUInt32LE(16, 16);
  head.writeUInt16LE(1, 20);
  head.writeUInt16LE(1, 22);
  head.writeUInt32LE(SR, 24);
  head.writeUInt32LE(SR * 2, 28);
  head.writeUInt16LE(2, 32);
  head.writeUInt16LE(16, 34);
  head.write('data', 36);
  head.writeUInt32LE(n * 2, 40);
  const data = Buffer.alloc(n * 2);
  for (let i = 0; i < n; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    data.writeInt16LE(Math.round(s * 32767), i * 2);
  }
  fs.writeFileSync(path.join(OUT, file), Buffer.concat([head, data]));
  console.log('wrote', file, (n / SR).toFixed(1) + 's');
}

const names = {
  handpan: '01-handpan-手碟.wav',
  kalimba: '02-kalimba-卡林巴.wav',
  marimba: '03-marimba-马林巴.wav',
  bowl: '04-bowl-颂钵.wav',
};

for (const [key, model] of Object.entries(INSTRUMENTS)) {
  const demo = normalize(renderDemo(model), 0.86);
  writeWav(names[key], demo);
}

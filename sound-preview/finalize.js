/*
 * 用 breathing-garden.html 里完全相同的合成函数，导出最终试听。
 *   final/<stage>.wav           —— 六个阶段提示音各一条
 *   final/box-4-4-4-4.wav       —— 方块呼吸两个循环的实际节奏
 *   final/478-4-7-8.wav         —— 4-7-8 两个循环（长屏息、长呼气）
 *
 * 运行：node finalize.js
 */
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'breathing-garden.html');
const src = fs.readFileSync(HTML, 'utf8');

function grabFn(name) {
  const start = src.indexOf('function ' + name + '(');
  if (start < 0) throw new Error('missing ' + name);
  let depth = 0;
  for (let j = src.indexOf('{', start); j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}') { depth--; if (depth === 0) return src.slice(start, j + 1); }
  }
  throw new Error('unbalanced ' + name);
}
function grabBlock(startMarker, endMarker) {
  const a = src.indexOf(startMarker);
  const b = src.indexOf(endMarker, a);
  if (a < 0 || b < 0) throw new Error('missing block ' + startMarker);
  return src.slice(a, b + endMarker.length);
}

eval(grabBlock('var HANDPAN=', '};'));
eval(grabFn('addNote'));
eval(grabFn('lowpassBuf'));
eval(grabFn('reverbBuf'));
eval(grabFn('renderCue'));
eval(grabBlock('var HAND_NOTES=', '};'));
eval(grabBlock('var CUE_DEFS=', '};'));

const SR = 20000;
function fakeCtx() {
  return {
    sampleRate: SR,
    createBuffer(ch, n, sr) {
      const d = new Float32Array(n);
      return { duration: n / sr, sampleRate: sr, length: n, getChannelData() { return d; } };
    },
  };
}

/* ── WAV ─────────────────────────────────────────────────── */
function writeWav(file, samples, sampleRate) {
  const n = samples.length;
  const head = Buffer.alloc(44);
  head.write('RIFF', 0);
  head.writeUInt32LE(36 + n * 2, 4);
  head.write('WAVE', 8);
  head.write('fmt ', 12);
  head.writeUInt32LE(16, 16);
  head.writeUInt16LE(1, 20);
  head.writeUInt16LE(1, 22);
  head.writeUInt32LE(sampleRate, 24);
  head.writeUInt32LE(sampleRate * 2, 28);
  head.writeUInt16LE(2, 32);
  head.writeUInt16LE(16, 34);
  head.write('data', 36);
  head.writeUInt32LE(n * 2, 40);
  const data = Buffer.alloc(n * 2);
  for (let i = 0; i < n; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    data.writeInt16LE(Math.round(s * 32767), i * 2);
  }
  fs.writeFileSync(file, Buffer.concat([head, data]));
  console.log('wrote', path.basename(file), (n / sampleRate).toFixed(1) + 's');
}

function normalize(dest, peak) {
  let max = 0;
  for (let i = 0; i < dest.length; i++) max = Math.max(max, Math.abs(dest[i]));
  if (max > 1e-9) {
    const k = peak / max;
    for (let i = 0; i < dest.length; i++) dest[i] *= k;
  }
  return dest;
}

/* ── 渲染六个提示音 ─────────────────────────────────────── */
const c = fakeCtx();
const cues = {};
for (const type of Object.keys(CUE_DEFS)) {
  const def = CUE_DEFS[type];
  cues[type] = renderCue(c, def.notes, def.dur, def.damp, def.peak);
}
const outDir = path.join(__dirname, 'final');
fs.mkdirSync(outDir, { recursive: true });
for (const type of Object.keys(cues)) {
  writeWav(path.join(outDir, type + '.wav'), cues[type].getChannelData(0), SR);
}

/* ── 把提示音按真实阶段时间铺到一条时间线上 ─────────────── */
function mixAt(dest, cue, atSec) {
  const off = Math.floor(atSec * SR);
  if (off >= dest.length) return;
  const data = cue.getChannelData(0);
  const n = Math.min(dest.length - off, data.length);
  for (let i = 0; i < n; i++) dest[off + i] += data[i];
}

function buildSequence(phases, cycles, tailSec) {
  const cycle = phases.reduce((a, p) => a + p.sec, 0);
  const total = cycle * cycles + tailSec;
  const n = Math.ceil(total * SR);
  const dest = new Float32Array(n);

  // 每个循环的阶段起点与呼气终点
  const starts = [];
  let t = 0, exhaleEnd = -1;
  for (const p of phases) {
    starts.push({ t, type: p.type });
    t += p.sec;
    if (p.type === 'exhale') exhaleEnd = t;
  }

  for (let k = 0; k < cycles; k++) {
    const base = k * cycle;
    for (const s of starts) mixAt(dest, cues[s.type], base + s.t);
    if (exhaleEnd > 0) mixAt(dest, cues.bloom, base + exhaleEnd);
  }
  // 最后一个循环结束后给一个收束
  mixAt(dest, cues.done, cycle * cycles);

  // 轻微首尾淡入淡出
  const fade = Math.floor(0.02 * SR);
  for (let i = 0; i < fade; i++) {
    dest[i] *= i / fade;
    dest[n - 1 - i] *= i / fade;
  }
  return dest;
}

const box = buildSequence([
  { sec: 4, type: 'inhale' },
  { sec: 4, type: 'hold' },
  { sec: 4, type: 'exhale' },
  { sec: 4, type: 'settle' },
], 2, 6);
writeWav(path.join(outDir, 'box-4-4-4-4.wav'), normalize(box, 0.80), SR);

const p478 = buildSequence([
  { sec: 4, type: 'inhale' },
  { sec: 7, type: 'hold' },
  { sec: 8, type: 'exhale' },
], 2, 6);
writeWav(path.join(outDir, '478-4-7-8.wav'), normalize(p478, 0.80), SR);

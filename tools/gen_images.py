#!/usr/bin/env python3
"""调用 rightapi.ai 的 gpt-image-2 生成呼吸花园素材（提交 → 轮询 → 下载）"""
import json, os, sys, io, time, urllib.request, urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_gen.log")


def log(msg):
    """直接写日志文件：后台运行时 stdout 缓冲不落盘，靠这个看进度"""
    line = time.strftime("[%H:%M:%S] ") + str(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        print(line, flush=True)
    except Exception:
        pass

def _load_env():
    """从 .env (gitignored) 读取密钥，避免密钥出现在命令行里"""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()
KEY = os.environ.get("RIGHTAPI_KEY", "")
BASE = "https://www.rightapi.ai"
SUBMIT = BASE + "/draw/v1/images/generations"
TASK = BASE + "/v1/tasks/"
MODEL = os.environ.get("IMG_MODEL", "gpt-image-2")
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BG = ("flat vector illustration, soft gradients, minimal calm storybook style, "
      "muted pastel palette, no outlines, wide 16:9 landscape, "
      "no text, no watermark, no people, no animals, no buildings")

JOBS = [
    # ---------- 背景 16:9 ----------
    ("bg-day.png", "16:9",
     "Flat vector illustration of a serene wide-open meadow landscape, soft gradients, minimal calm "
     "storybook style, muted pastel palette, no outlines. Bright clear blue sky at the top fading to "
     "pale warm white near the horizon, a few soft fluffy white clouds. Middle band: four layers of "
     "rolling hills in soft silhouettes, each layer successively lighter and hazier toward the distance "
     "for deep atmospheric perspective. Lower 40 percent: a wide empty green meadow with fine subtle "
     "grass texture, completely open and uncluttered, no flowers, no trees, no objects. The center of "
     "the image is empty sky and distant hills with no focal subject. Gentle sunlight from the right. "
     "Wide 16:9 landscape aspect ratio. No text, no watermark, no people, no animals, no buildings."),

    ("bg-dawn.png", "16:9",
     "Flat vector illustration of a serene wide-open meadow landscape at dawn, soft gradients, minimal "
     "calm storybook style, muted pastel palette, no outlines. Soft pink and peach dawn sky at the top "
     "fading to pale golden light near the horizon, thin wispy clouds catching warm light. Middle band: "
     "four layers of rolling hills in soft misty silhouettes, tinted lavender and dusty rose, each layer "
     "successively lighter and hazier toward the distance for deep atmospheric perspective. Lower 40 "
     "percent: a wide empty cool green meadow with fine subtle grass texture, completely open and "
     "uncluttered, no flowers, no trees, no objects. The center of the image is empty sky and distant "
     "hills with no focal subject. Wide 16:9 landscape aspect ratio. No text, no watermark, no people, "
     "no animals, no buildings."),

    ("bg-dusk.png", "16:9",
     "Flat vector illustration of a serene wide-open meadow landscape at sunset, soft gradients, minimal "
     "calm storybook style, muted pastel palette, no outlines. Warm orange and coral sunset sky at the "
     "top fading to bright golden glow near the horizon, a few soft clouds rimmed with light. Middle "
     "band: four layers of rolling hills in soft deep silhouettes, tinted purple and dusty mauve, each "
     "layer successively lighter and hazier toward the distance for deep atmospheric perspective. Lower "
     "40 percent: a wide empty olive green meadow with fine subtle grass texture, completely open and "
     "uncluttered, no flowers, no trees, no objects. The center of the image is empty sky and distant "
     "hills with no focal subject. Wide 16:9 landscape aspect ratio. No text, no watermark, no people, "
     "no animals, no buildings."),

    ("bg-night.png", "16:9",
     "Flat vector illustration of a serene wide-open meadow landscape at night, soft gradients, minimal "
     "calm storybook style, muted pastel palette, no outlines. Deep navy blue night sky at the top with "
     "a scattering of faint small stars, fading to a soft cool glow near the horizon, one pale crescent "
     "moon high on the right, a few faint wispy clouds. Middle band: four layers of rolling hills in "
     "soft silhouettes, tinted cool blue-grey, each layer successively lighter and hazier toward the "
     "distance for deep atmospheric perspective. Lower 40 percent: a wide empty dark teal meadow with "
     "fine subtle grass texture, completely open and uncluttered, no flowers, no trees, no objects. The "
     "center of the image is empty sky and distant hills with no focal subject. Wide 16:9 landscape "
     "aspect ratio. No text, no watermark, no people, no animals, no buildings."),

    # ---------- 花朵 1:1 纯白背景 ----------
    ("flower-star-pink.png", "1:1",
     "Flat vector illustration of a single round pink flower with six symmetrical pointed petals, a "
     "straight thin green stem, and two small green leaves. Viewed straight-on from the front, perfectly "
     "centered. Soft gradient petals with a small bright center, minimal calm storybook style, muted "
     "pastel palette, no outlines. Fully isolated on a pure solid white background with no shadow, no "
     "ground, no gradient background, no other elements. Square 1:1 aspect ratio. No text, no watermark."),

    ("flower-star-yellow.png", "1:1",
     "Flat vector illustration of a single round soft yellow flower with six symmetrical pointed petals, "
     "a straight thin green stem, and two small green leaves. Viewed straight-on from the front, "
     "perfectly centered. Soft gradient petals with a small bright center, minimal calm storybook style, "
     "muted pastel palette, no outlines. Fully isolated on a pure solid white background with no shadow, "
     "no ground, no gradient background, no other elements. Square 1:1 aspect ratio. No text, no watermark."),

    ("flower-bell-violet.png", "1:1",
     "Flat vector illustration of a single soft violet flower with five wide rounded petals that gently "
     "droop downward, a gracefully curved green stem, and two small leaves. Viewed straight-on from the "
     "front, perfectly centered. Soft gradient petals, minimal calm storybook style, muted pastel "
     "palette, no outlines. Fully isolated on a pure solid white background with no shadow, no ground, "
     "no gradient background, no other elements. Square 1:1 aspect ratio. No text, no watermark."),

    ("flower-bell-coral.png", "1:1",
     "Flat vector illustration of a single soft coral orange flower with five wide rounded petals that "
     "gently droop downward, a gracefully curved green stem, and two small leaves. Viewed straight-on "
     "from the front, perfectly centered. Soft gradient petals, minimal calm storybook style, muted "
     "pastel palette, no outlines. Fully isolated on a pure solid white background with no shadow, no "
     "ground, no gradient background, no other elements. Square 1:1 aspect ratio. No text, no watermark."),

    ("flower-reed-blue.png", "1:1",
     "Flat vector illustration of a single slender light blue flower with nine narrow elongated petals "
     "radiating outward like a delicate wildflower, a tall thin slightly curved green stem, and two "
     "slender leaves. Viewed straight-on from the front, perfectly centered. Soft gradient petals, "
     "minimal calm storybook style, muted pastel palette, no outlines. Fully isolated on a pure solid "
     "white background with no shadow, no ground, no gradient background, no other elements. Square 1:1 "
     "aspect ratio. No text, no watermark."),

    ("flower-reed-magenta.png", "1:1",
     "Flat vector illustration of a single slender magenta pink flower with nine narrow elongated petals "
     "radiating outward like a delicate wildflower, a tall thin slightly curved green stem, and two "
     "slender leaves. Viewed straight-on from the front, perfectly centered. Soft gradient petals, "
     "minimal calm storybook style, muted pastel palette, no outlines. Fully isolated on a pure solid "
     "white background with no shadow, no ground, no gradient background, no other elements. Square 1:1 "
     "aspect ratio. No text, no watermark."),
]


def req(url, data=None, method=None):
    h = {"Authorization": "Bearer " + KEY,
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if data is not None:
        h["Content-Type"] = "application/json"
        h["Accept"] = "application/json"
        data = json.dumps(data).encode()
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code} on {url}\n  body: {body[:500]}") from None


def probe():
    """诊断：逐条试端点，打印服务端原始响应"""
    tests = [
        ("POST", BASE + "/draw/v1/images/generations",
         {"model": MODEL, "prompt": "a calm flat vector meadow", "n": 1,
          "size": "16:9", "imageSize": "1K", "async": True}),
        ("POST", BASE + "/v1/images/generations",
         {"model": MODEL, "prompt": "test", "n": 1, "size": "1:1", "async": True}),
    ]
    for method, url, body in tests:
        print(f"--- {method} {url}")
        try:
            print("   ", json.dumps(req(url, body), ensure_ascii=False)[:400])
        except Exception as e:
            print("    ERR:", str(e)[:600])
    print("--- GET /v1/models")
    try:
        d = req(BASE + "/v1/models")
        ids = [m.get("id") for m in d.get("data", [])]
        print("    models:", [i for i in ids if "image" in str(i).lower() or "banana" in str(i).lower()][:20] or ids[:20])
    except Exception as e:
        print("    ERR:", str(e)[:400])


def retry(fn, tries=5, label="op"):
    """中继站会瞬时断连，统一重试"""
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            log(f"    [{label}] 第{i+1}次失败: {str(e)[:120]}")
            time.sleep(3 * (i + 1))
    raise last


def submit(prompt, size):
    return retry(lambda: req(SUBMIT, {"model": MODEL, "prompt": prompt, "n": 1,
                                      "size": size, "imageSize": "1K", "async": True}),
                 label="submit")


def poll(task_id, timeout=900):
    t0 = time.time()
    last = ""
    while time.time() - t0 < timeout:
        try:
            d = req(TASK + task_id)
        except Exception as e:
            log(f"    [poll] 瞬时错误，继续等待: {str(e)[:100]}")
            time.sleep(6); continue
        st = d.get("status", "")
        if st != last:
            log(f"    status={st!r} progress={d.get('progress')}")
            last = st
        # 完成态有两种形态：显式 completed，或直接返回 {created, data:[{url}]}（无 status 字段）
        if st == "completed" or d.get("data") or d.get("candidates"):
            log("    完成")
            return d
        if st == "failed":
            raise RuntimeError("task failed: " + json.dumps(d.get("error", {}), ensure_ascii=False))
        time.sleep(5)
    raise TimeoutError("poll timeout")


def extract_url(d):
    if isinstance(d.get("data"), list) and d["data"]:
        it = d["data"][0]
        if it.get("url"):
            return it["url"]
        if it.get("b64_json"):
            return None
    for c in d.get("candidates", []):
        for p in c.get("content", {}).get("parts", []):
            if p.get("text", "").startswith("http"):
                return p["text"].strip()
    return None


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    if not KEY:
        print("ERROR: 请设置环境变量 RIGHTAPI_KEY")
        sys.exit(1)
    if only and only[0] == "--probe":
        probe(); return
    os.makedirs(OUT, exist_ok=True)
    log(f"=== 开始生成（模型 {MODEL}，共 {len(JOBS)} 张）===")
    for name, size, prompt in JOBS:
        if only and name not in only:
            continue
        dest = os.path.join(OUT, name)
        if os.path.exists(dest) and not only:
            log(f"[skip] {name} 已存在"); continue
        log(f"[{name}] 提交中…")
        try:
            r = submit(prompt, size)
            tid = r.get("task_id")
            log(f"    task_id={tid}")
            d = poll(tid)
            url = extract_url(d)
            if not url:
                log("    未找到图片 URL: " + json.dumps(d, ensure_ascii=False)[:400]); continue
            blob = retry(lambda: urllib.request.urlopen(url, timeout=120).read(), label="download")
            with open(dest, "wb") as f:
                f.write(blob)
            log(f"    OK 已保存 {name} ({len(blob)//1024} KB)")
        except Exception as e:
            log(f"    FAIL {name}: {str(e)[:300]}")


if __name__ == "__main__":
    main()

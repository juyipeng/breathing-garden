#!/bin/bash
# 构建安卓 APK。改了 breathing-garden.html 之后跑这个即可。
#
# 机器相关的路径写在 build.env（参考 build.env.example），或直接用同名环境变量：
#   JAVA_HOME / ANDROID_HOME / GRADLE_USER_HOME / GRADLE_DIST_URL
set -e
cd "$(dirname "$0")"

# shellcheck disable=SC1091
[ -f build.env ] && . ./build.env

if [ -z "$JAVA_HOME" ] || [ ! -d "$JAVA_HOME" ]; then
  echo "错误：JAVA_HOME 未设置或不存在。请复制 build.env.example 为 build.env 并填入 JDK 21 路径。" >&2
  exit 1
fi
ANDROID_HOME="${ANDROID_HOME:-$ANDROID_SDK_ROOT}"
if [ -z "$ANDROID_HOME" ] || [ ! -d "$ANDROID_HOME" ]; then
  echo "错误：ANDROID_HOME 未设置或不存在。请复制 build.env.example 为 build.env 并填入 Android SDK 路径。" >&2
  exit 1
fi
export JAVA_HOME ANDROID_HOME
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export GRADLE_USER_HOME="${GRADLE_USER_HOME:-$HOME/.gradle}"

APP="capacitor"
WRAPPER="$APP/android/gradle/wrapper/gradle-wrapper.properties"

# 某些网络环境下 Java 连不上 services.gradle.org，可用本地分发包。
# 只临时改写 wrapper，构建结束（无论成败）自动还原。
if [ -n "$GRADLE_DIST_URL" ]; then
  cp "$WRAPPER" "$WRAPPER.orig"
  trap 'mv -f "$WRAPPER.orig" "$WRAPPER"' EXIT
  sed -i "s|^distributionUrl=.*|distributionUrl=$GRADLE_DIST_URL|" "$WRAPPER"
fi

echo "==> 同步 web 资产到 Capacitor 工程"
mkdir -p "$APP/www"
cp breathing-garden.html    "$APP/www/index.html"
cp manifest.webmanifest     "$APP/www/"
cp sw.js icon-192.png icon-512.png "$APP/www/"

echo "==> cap sync"
(cd "$APP" && npx cap sync android >/dev/null)

echo "==> gradle assembleDebug"
(cd "$APP/android" && ./gradlew assembleDebug --no-daemon --console=plain -q)

OUT="$APP/android/app/build/outputs/apk/debug/app-debug.apk"
cp "$OUT" ./breathing-garden.apk
echo
echo "完成 -> breathing-garden.apk  ($(du -h ./breathing-garden.apk | cut -f1))"
echo
echo "装到手机（需先开 USB 调试）："
echo "  \$ANDROID_HOME/platform-tools/adb install -r breathing-garden.apk"

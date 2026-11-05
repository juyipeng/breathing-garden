package com.breathinggarden.app;

import android.os.PowerManager;
import android.webkit.JavascriptInterface;

/**
 * 暴露给网页的最小接口：只负责会话期间的 partial wake lock。
 *
 * 单独放一个顶层类，不写成 MainActivity 的内部类 —— 内部类会带上
 * NestHost/NestMembers 属性，AGP 8.x 的增量 dex 在只重新编译成员类时
 * 偶发 "nest host ... on program or class path" 报错。
 */
public class SessionWakeLockBridge {

    private final PowerManager.WakeLock wakeLock;

    SessionWakeLockBridge(PowerManager.WakeLock wakeLock) {
        this.wakeLock = wakeLock;
    }

    /** 会话开始 / 从暂停恢复 / 打开声音时调用 */
    @JavascriptInterface
    public void startSession() {
        if (wakeLock != null && !wakeLock.isHeld()) {
            try {
                wakeLock.acquire(6L * 60L * 60L * 1000L);   /* 最长 6 小时兜底 */
            } catch (Exception ignored) {}
        }
    }

    /** 暂停 / 结束 / 关闭全部声音时调用 */
    @JavascriptInterface
    public void stopSession() {
        if (wakeLock != null && wakeLock.isHeld()) {
            try {
                wakeLock.release();
            } catch (Exception ignored) {}
        }
    }
}

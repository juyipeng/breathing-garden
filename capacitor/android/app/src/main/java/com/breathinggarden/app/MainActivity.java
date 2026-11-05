package com.breathinggarden.app;

import android.os.Bundle;
import android.os.PowerManager;

import com.getcapacitor.BridgeActivity;

/**
 * 呼吸花园的安卓壳。
 *
 * 网页把整段会话的提示音提前排在 Web Audio 的时间轴上，息屏后不依赖
 * JS 定时器也能照常响。这里再补一件事：会话进行中持有 partial wake lock，
 * 免得设备在两次提示音之间进入深睡，把音频线程一起挂起。
 *
 * 只在「正在练习且开着提示音或环境音」时持有，暂停/结束即释放。
 */
public class MainActivity extends BridgeActivity {

    private PowerManager.WakeLock wakeLock;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
        if (pm != null) {
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "BreathingGarden:Session");
            wakeLock.setReferenceCounted(false);
        }

        try {
            getBridge().getWebView().addJavascriptInterface(
                    new SessionWakeLockBridge(wakeLock), "BreathingGardenNative");
        } catch (Exception ignored) {
            /* 注入失败不影响应用本身，只是少了息屏保底 */
        }
    }

    @Override
    public void onDestroy() {
        if (wakeLock != null && wakeLock.isHeld()) {
            try {
                wakeLock.release();
            } catch (Exception ignored) {}
        }
        super.onDestroy();
    }
}

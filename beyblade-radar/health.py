"""監控健康警示:某平台連續失敗太多次就通知你一次,恢復時再通知一次。

「一定要第一時間收到」的需求下,最怕的是監控其實壞了(被擋、改版、斷線)你卻不知道。
狀態存在 Calendar 的 meta 表,所以常駐程式重啟、或 GitHub Actions 每輪重開都記得。
"""

from __future__ import annotations

from typing import Optional

from calendar_db import Calendar


class HealthTracker:
    def __init__(self, cal: Calendar, threshold: int = 3):
        self.cal = cal
        self.threshold = max(1, threshold)

    def update(self, platform: str, error: Optional[str]) -> Optional[str]:
        """回報這一輪的結果;需要通知時回傳訊息文字,否則 None。"""
        fail_key, warned_key = f"health:{platform}:fails", f"health:{platform}:warned"
        fails = int(self.cal.get_meta(fail_key, "0") or 0)
        warned = self.cal.get_meta(warned_key, "0") == "1"

        if error is None:
            self.cal.set_meta(fail_key, "0")
            if warned:
                self.cal.set_meta(warned_key, "0")
                return f"✅【監控恢復】{platform_label(platform)} 已恢復正常。"
            return None

        fails += 1
        self.cal.set_meta(fail_key, str(fails))
        if fails >= self.threshold and not warned:
            self.cal.set_meta(warned_key, "1")
            return (
                f"⚠️【監控失敗】{platform_label(platform)} 已連續 {fails} 輪失敗,"
                f"這段期間不會收到它的通知。\n原因:{error}"
            )
        return None


def platform_label(platform: str) -> str:
    return {"biccamera": "ビックカメラ", "rakuten_jp": "樂天市場"}.get(platform, platform)

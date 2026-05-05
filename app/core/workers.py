from ..common import *

# =========================================================
# 2. API Workers
# =========================================================

class APIRenderWorker(QThread):
    log = Signal(str)
    done = Signal(dict)

    def __init__(self, task, cfg):
        super().__init__()
        self.task = task
        self.cfg = cfg
        self.cancelled = False
        self.session = requests.Session() if requests else None
        self.current_task_id = ""
        self.start_time = 0

    def emit_log(self, msg):
        self.log.emit(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def fail(self, msg):
        self.done.emit({"ok": False, "msg": msg, "task_id": self.current_task_id})

    def upload_tos(self, path):
        if str(path).startswith(("http://", "https://", "asset://")):
            return path
        if not self.cfg.get("enable_tos_upload"):
            raise RuntimeError("当前引用了本地素材，但未启用 TOS 本地上传。请在管线设置 > TOS 上传中开启并填写配置，或改用公网 URL / asset://素材。")
        if tos is None:
            raise RuntimeError("缺少 TOS SDK。请先 pip install tos，或改用公网 URL / asset://素材。")
        for key in ["tos_bucket", "tos_endpoint", "tos_access_key", "tos_secret_key"]:
            if not self.cfg.get(key):
                raise RuntimeError("TOS 配置不完整。Bucket、Endpoint、AccessKey、SecretKey 只在启用本地素材上传时必填。")
        client = tos.TosClientV2(
            self.cfg["tos_access_key"],
            self.cfg["tos_secret_key"],
            self.cfg["tos_endpoint"],
            region="cn-beijing"
        )
        ext = os.path.splitext(path)[1]
        obj = f"vfx_pipeline/{int(time.time())}_{os.path.basename(path)}"
        client.put_object_from_file(self.cfg["tos_bucket"], obj, path)
        ep = self.cfg["tos_endpoint"].replace("https://", "").replace("http://", "")
        if not ep.startswith("http"):
            url = f"https://{self.cfg['tos_bucket']}.{ep}/{obj}"
        else:
            url = f"{ep}/{obj}"
        return url

    def build_content(self):
        prompt = self.task.get("prompt", "")
        official_prompt = prompt
        content = []
        counters = {"image": 1, "video": 1, "audio": 1}

        model_name = str(self.task.get("model_profile") or "")
        is_seedance_1_fast = (model_name == "Doubao-Seedance-1.0-pro-fast")
        first_frame_used = False

        refs = self.task.get("refs", []) or []
        self.emit_log(f"本次提交 refs 数量：{len(refs)}")

        for ref in refs:
            tag = ref.get("tag", "")
            path = ref.get("path", "")
            kind = ref.get("kind") or asset_kind(path, tag)
            if not path:
                continue

            # seedance 1.0 pro fast 只支持文生视频 / 图生视频-首帧
            # 不支持 reference_video / reference_audio / reference_image
            if is_seedance_1_fast and kind in ("video", "audio"):
                self.emit_log(f"已忽略不支持的参考素材：{tag}（{kind}）")
                continue

            if is_seedance_1_fast and kind == "image" and first_frame_used:
                self.emit_log(f"已忽略多余图片参考：{tag}（该模型只保留 1 张首帧图）")
                continue

            if not str(path).startswith(("http://", "https://", "asset://")):
                self.emit_log(f"上传素材到 TOS：{tag}")
                path = self.upload_tos(path)

            if kind == "video":
                official_prompt = official_prompt.replace(f"[@{tag}]", f"[视频{counters['video']}]")
                content.append({"type": "video_url", "video_url": {"url": path}, "role": "reference_video"})
                counters["video"] += 1
            elif kind == "audio":
                official_prompt = official_prompt.replace(f"[@{tag}]", f"[音频{counters['audio']}]")
                content.append({"type": "audio_url", "audio_url": {"url": path}, "role": "reference_audio"})
                counters["audio"] += 1
            else:
                if is_seedance_1_fast:
                    # 1.0 pro fast 单图时应走“首帧图生视频”，不能走 reference_image
                    official_prompt = official_prompt.replace(f"[@{tag}]", "")
                    content.append({"type": "image_url", "image_url": {"url": path}, "role": "first_frame"})
                    first_frame_used = True
                    self.emit_log(f"图片素材按首帧图提交：{tag}")
                else:
                    official_prompt = official_prompt.replace(f"[@{tag}]", f"[图{counters['image']}]")
                    content.append({"type": "image_url", "image_url": {"url": path}, "role": "reference_image"})
                    counters["image"] += 1

        official_prompt = re.sub(r'\s{2,}', ' ', official_prompt).strip()

        if official_prompt:
            content.insert(0, {"type": "text", "text": official_prompt})
        return content

    def submit_payload(self):
        mode = self.task.get("mode")
        model_name = str(self.task.get("model_profile") or "")
        is_seedance_1_fast = (model_name == "Doubao-Seedance-1.0-pro-fast")

        payload = {
            "model": self.task.get("endpoint"),
            "content": self.build_content(),
            "ratio": self.task.get("ratio", "16:9"),
        }
        if self.task.get("seed", -1) != -1:
            payload["seed"] = self.task.get("seed")
        if mode == "video":
            payload.update({
                "resolution": self.task.get("resolution", "720p"),
                "duration": self.task.get("duration", 5),
                "return_last_frame": (False if is_seedance_1_fast else True),
                "watermark": False,
            })

            service_tier = str(self.task.get("service_tier") or "default").strip().lower()
            supports_offline = bool(self.task.get("supports_offline_inference")) or is_seedance_1_fast

            if service_tier == "flex":
                if supports_offline:
                    payload["service_tier"] = "flex"
                    try:
                        expires = int(self.task.get("execution_expires_after") or 172800)
                    except Exception:
                        expires = 172800
                    expires = max(3600, min(expires, 259200))
                    payload["execution_expires_after"] = expires
                    self.emit_log(f"推理层级：离线推理（flex），最大等待 {expires} 秒")
                else:
                    self.emit_log("当前模型不支持离线推理，已自动回退为在线推理。")
            else:
                # 在线推理时不要主动发送 service_tier=default。
                # 某些模型 / 某些任务类型要求该字段为空。
                self.emit_log("推理层级：在线推理（省略 service_tier 参数）")

            if self.task.get("enable_web_search") and not is_seedance_1_fast:
                payload["tools"] = [{"type": "web_search"}]
        else:
            payload.update({
                "resolution": self.task.get("resolution", "2k"),
                "watermark": False,
            })
        return payload

    def run(self):
        if requests is None:
            self.fail("缺少 requests，请先安装 requests。")
            return
        if not self.cfg.get("api_key"):
            self.fail("未配置 API Key。")
            return
        if not self.task.get("endpoint"):
            self.fail("当前模型没有配置 Endpoint。")
            return

        self.start_time = time.time()
        headers = {"Authorization": f"Bearer {self.cfg['api_key']}", "Content-Type": "application/json"}
        try:
            payload = self.submit_payload()
            self.emit_log("提交云端任务...")
            res = self.session.post(BASE_URL, headers=headers, json=payload, timeout=60)
            if res.status_code >= 400:
                self.fail(f"提交失败：{res.status_code}\n{res.text}")
                return
            data = res.json()
            self.current_task_id = data.get("id") or data.get("task_id") or data.get("data", {}).get("id", "")
            if not self.current_task_id:
                self.fail(f"提交成功但没有返回任务 ID：{json.dumps(data, ensure_ascii=False)[:800]}")
                return
            self.emit_log(f"任务 ID：{self.current_task_id}")

            delay = int(self.cfg.get("poll_delay", 45))
            interval = int(self.cfg.get("poll_interval", 5))
            if delay > 0:
                time.sleep(delay)

            url = f"{BASE_URL}/{self.current_task_id}"
            raw_result = {}
            while not self.cancelled:
                q = self.session.get(url, headers=headers, timeout=40)
                if q.status_code >= 400:
                    self.fail(f"查询失败：{q.status_code}\n{q.text}")
                    return
                raw_result = q.json()
                status = str(raw_result.get("status", "")).lower()
                self.emit_log(f"云端状态：{status}")
                if status in {"succeeded", "success", "completed"}:
                    break
                if status in {"failed", "cancelled", "expired"}:
                    self.fail(f"任务失败：{json.dumps(raw_result, ensure_ascii=False)[:1200]}")
                    return
                time.sleep(interval)

            media_url = extract_url(raw_result)
            if not media_url:
                self.fail("任务成功，但没有找到可下载 URL。")
                return

            ext = guess_ext_from_url(media_url, "mp4" if self.task.get("mode") == "video" else "png")
            out_dir = self.task.get("output_dir") or self.cfg.get("output_dir")
            fp = get_next_path(out_dir, self.task.get("project", "Project"), self.task.get("shot", "Shot"), ext)
            self.emit_log("开始下载生成结果...")
            
            # 安全下载，防止抢占冲突
            try:
                temp_fp = f"{fp}.{int(time.time() * 1000)}.tmp"
                with self.session.get(media_url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(temp_fp, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if self.cancelled:
                                f.close()
                                if os.path.exists(temp_fp): os.remove(temp_fp)
                                self.fail("任务被用户强行熔断停止。")
                                return
                            if chunk:
                                f.write(chunk)
                
                if os.path.exists(fp):
                    fp = fp.replace(f".{ext}", f"_{int(time.time() * 1000)}.{ext}")
                os.rename(temp_fp, fp)
            except Exception as e:
                self.fail(f"下载文件到本地失败: {e}")
                if 'temp_fp' in locals() and os.path.exists(temp_fp):
                    os.remove(temp_fp)
                return

            elapsed = round(time.time() - self.start_time, 2)
            meta = {
                "task_id": self.current_task_id,
                "mode": self.task.get("mode"),
                "model_profile": self.task.get("model_profile"),
                "endpoint": self.task.get("endpoint"),
                "project": self.task.get("project"),
                "shot": self.task.get("shot"),
                "prompt": self.task.get("prompt"),
                "negative_prompt": self.task.get("negative_prompt", ""),
                "seed": self.task.get("seed", -1),
                "ratio": self.task.get("ratio"),
                "resolution": self.task.get("resolution"),
                "duration": self.task.get("duration"),
                "video_mode": self.task.get("video_mode", ""),
                "service_tier": str(self.task.get("service_tier") or "default"),
                "refs": self.task.get("refs", []),
                "created_at": now_str(),
                "elapsed_seconds": elapsed,
                "url": media_url,
                "usage_total_tokens": get_usage_tokens(raw_result),
                "raw": json.dumps(raw_result, ensure_ascii=False, indent=2)
            }
            write_sidecar(fp, meta)
            self.done.emit({"ok": True, "path": fp, "task_id": self.current_task_id, "time": elapsed, "url": media_url})
        except Exception as e:
            self.fail(str(e))


class QueryWorker(QThread):
    done = Signal(dict)

    def __init__(self, api_key, task_id):
        super().__init__()
        self.api_key = api_key
        self.task_id = task_id

    def run(self):
        if requests is None:
            self.done.emit({"ok": False, "msg": "缺少 requests。"})
            return
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            res = requests.get(f"{BASE_URL}/{self.task_id}", headers=headers, timeout=40)
            if res.status_code >= 400:
                self.done.emit({"ok": False, "msg": f"{res.status_code}\n{res.text}"})
                return
            data = res.json()
            self.done.emit({
                "ok": True,
                "raw": json.dumps(data, ensure_ascii=False, indent=2),
                "status": data.get("status", ""),
                "url": extract_url(data),
                "thumb": extract_thumb(data),
                "usage_total_tokens": get_usage_tokens(data),
                "model": data.get("model", "")
            })
        except Exception as e:
            self.done.emit({"ok": False, "msg": str(e)})


class ScanCloudWorker(QThread):
    done = Signal(dict)

    def __init__(self, api_key, limit=24):
        super().__init__()
        self.api_key = api_key
        self.limit = limit

    def run(self):
        if requests is None:
            self.done.emit({"ok": False, "msg": "缺少 requests。"})
            return
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            params = {"page_num": 1, "page_size": self.limit, "filter.status": "succeeded"}
            res = requests.get(BASE_URL, headers=headers, params=params, timeout=60)
            if res.status_code >= 400:
                self.done.emit({"ok": False, "msg": f"{res.status_code}\n{res.text}"})
                return
            data = res.json()
            items = data.get("items") or data.get("data", {}).get("items") or data.get("data", []) or []
            tasks = []
            for it in items:
                task_id = it.get("id") or it.get("task_id") or ""
                url = extract_url(it)
                thumb = extract_thumb(it)
                if not task_id:
                    continue
                created = it.get("created_at") or ""
                updated = it.get("updated_at") or ""
                elapsed = ""
                try:
                    c = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
                    u = datetime.datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    elapsed = int((u - c).total_seconds())
                except Exception:
                    pass
                tasks.append({
                    "task_id": task_id,
                    "status": it.get("status", ""),
                    "url": url,
                    "thumb": thumb,
                    "created_at": created,
                    "updated_at": updated,
                    "elapsed_seconds": elapsed,
                    "usage_total_tokens": get_usage_tokens(it),
                    "model": it.get("model", ""),
                    "raw": json.dumps(it, ensure_ascii=False, indent=2)
                })
            self.done.emit({"ok": True, "tasks": tasks, "raw": json.dumps(data, ensure_ascii=False, indent=2)})
        except Exception as e:
            self.done.emit({"ok": False, "msg": str(e)})



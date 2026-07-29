"""Simple tkinter front-end for whisper.py: pick video files or a folder and transcribe."""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

FROZEN = getattr(sys, "frozen", False)
# When frozen, whisper.py is built as a sibling console executable next to the GUI.
APP_DIR = (
    os.path.dirname(os.path.abspath(sys.executable))
    if FROZEN
    else os.path.dirname(os.path.abspath(__file__))
)
WORKER = (
    os.path.join(APP_DIR, "fw-worker.exe" if os.name == "nt" else "fw-worker")
    if FROZEN
    else os.path.join(APP_DIR, "whisper.py")
)

FILE_TYPES = [
    (
        "影片 / 音訊",
        "*.mp4 *.mkv *.mov *.webm *.avi *.flv *.mp3 *.wav *.aac *.m4a *.flac *.ogg",
    ),
    ("所有檔案", "*.*"),
]
MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Faster Whisper SRT")
        self.geometry("760x560")
        self.minsize(640, 480)

        self.targets = []
        self.proc = None
        self.output = queue.Queue()

        self._build_widgets()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._drain_output)

    # ---------- layout ----------
    def _build_widgets(self):
        pad = {"padx": 8, "pady": 4}

        picker = ttk.Frame(self)
        picker.pack(fill="x", **pad)
        ttk.Button(picker, text="選檔案…", command=self.add_files).pack(side="left")
        ttk.Button(picker, text="選資料夾…", command=self.add_folder).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(picker, text="移除選取", command=self.remove_selected).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(picker, text="全部清除", command=self.clear_targets).pack(
            side="left", padx=(6, 0)
        )

        list_frame = ttk.LabelFrame(self, text="待處理清單")
        list_frame.pack(fill="both", expand=False, **pad)
        self.listbox = tk.Listbox(list_frame, height=6, selectmode="extended")
        self.listbox.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        list_scroll = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.listbox.yview
        )
        list_scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=list_scroll.set)

        opts = ttk.LabelFrame(self, text="設定")
        opts.pack(fill="x", **pad)

        self.model_var = tk.StringVar(value="medium")
        self.language_var = tk.StringVar(value="zh")
        self.keywords_var = tk.StringVar(value="")
        self.offset_var = tk.StringVar(value="0")

        ttk.Label(opts, text="模型").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Combobox(
            opts, textvariable=self.model_var, values=MODELS, width=12, state="readonly"
        ).grid(row=0, column=1, sticky="w", pady=4)

        ttk.Label(opts, text="語言").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(opts, textvariable=self.language_var, width=8).grid(
            row=0, column=3, sticky="w", pady=4
        )

        ttk.Label(opts, text="時間軸偏移 (ms)").grid(
            row=0, column=4, sticky="w", padx=6, pady=4
        )
        ttk.Spinbox(
            opts,
            textvariable=self.offset_var,
            from_=-5000,
            to=5000,
            increment=50,
            width=8,
        ).grid(row=0, column=5, sticky="w", pady=4)

        ttk.Label(opts, text="關鍵字").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(opts, textvariable=self.keywords_var).grid(
            row=1, column=1, columnspan=5, sticky="ew", padx=(0, 6), pady=4
        )
        opts.columnconfigure(5, weight=1)

        actions = ttk.Frame(self)
        actions.pack(fill="x", **pad)
        self.start_btn = ttk.Button(actions, text="開始轉錄", command=self.start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(
            actions, text="停止", command=self.stop, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=(6, 0))
        self.status_var = tk.StringVar(value="請先選擇檔案或資料夾")
        ttk.Label(actions, textvariable=self.status_var).pack(side="left", padx=(12, 0))

        log_frame = ttk.LabelFrame(self, text="輸出")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log = tk.Text(log_frame, wrap="none", state="disabled", height=12)
        self.log.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        log_scroll = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log.yview
        )
        log_scroll.pack(side="right", fill="y")
        self.log.config(yscrollcommand=log_scroll.set)

    # ---------- target list ----------
    def add_files(self):
        paths = filedialog.askopenfilenames(title="選擇影片或音訊檔", filetypes=FILE_TYPES)
        self._add_targets(paths)

    def add_folder(self):
        path = filedialog.askdirectory(title="選擇資料夾")
        if path:
            self._add_targets([path])

    def _add_targets(self, paths):
        for path in paths:
            path = os.path.normpath(path)
            if path not in self.targets:
                self.targets.append(path)
                self.listbox.insert("end", path)
        self._update_status()

    def remove_selected(self):
        for index in reversed(self.listbox.curselection()):
            self.listbox.delete(index)
            del self.targets[index]
        self._update_status()

    def clear_targets(self):
        self.listbox.delete(0, "end")
        self.targets.clear()
        self._update_status()

    def _update_status(self):
        if self.proc:
            return
        if self.targets:
            self.status_var.set(f"已選擇 {len(self.targets)} 個項目")
        else:
            self.status_var.set("請先選擇檔案或資料夾")

    # ---------- run ----------
    def start(self):
        if self.proc:
            return
        if not self.targets:
            messagebox.showinfo("提醒", "請先選擇檔案或資料夾")
            return
        try:
            offset = int(self.offset_var.get())
        except ValueError:
            messagebox.showerror("設定錯誤", "時間軸偏移必須是整數（毫秒）")
            return

        cmd = [
            *([WORKER] if FROZEN else [sys.executable, "-u", WORKER]),
            *self.targets,
            "--model",
            self.model_var.get(),
            "--language",
            self.language_var.get().strip() or "zh",
            "--keywords",
            self.keywords_var.get(),
            "--offset",
            str(offset),
        ]

        self._clear_log()
        self._append_log(" ".join(cmd) + "\n\n")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("轉錄中…")

        threading.Thread(target=self._run, args=(cmd,), daemon=True).start()

    def _run(self, cmd):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            self.proc = subprocess.Popen(
                cmd,
                cwd=APP_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
                env=env,
                **kwargs,
            )
        except OSError as exc:
            self.proc = None
            self.output.put(("line", f"無法啟動：{exc}\n"))
            self.output.put(("done", -1))
            return

        for line in self.proc.stdout:
            self.output.put(("line", line))
        code = self.proc.wait()
        self.proc = None
        self.output.put(("done", code))

    def stop(self):
        if self.proc:
            self.proc.terminate()
            self.status_var.set("停止中…")

    # ---------- log ----------
    def _drain_output(self):
        try:
            while True:
                kind, payload = self.output.get_nowait()
                if kind == "line":
                    self._append_log(payload)
                else:
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    if payload == 0:
                        self.status_var.set("完成")
                    else:
                        self.status_var.set(f"結束（代碼 {payload}）")
        except queue.Empty:
            pass
        self.after(100, self._drain_output)

    def _append_log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _on_close(self):
        if self.proc:
            if not messagebox.askokcancel("確認", "轉錄還在進行，要結束嗎？"):
                return
            self.proc.terminate()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()

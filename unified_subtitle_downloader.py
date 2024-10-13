import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import re
import json
import threading
from v1 import get_subtitles as get_youtube_subtitles
from bilibili_subtitle import get_subtitles as get_bilibili_subtitles

class UnifiedSubtitleApp:
    def __init__(self, master):
        self.master = master
        master.title("统一字幕下载器")
        master.geometry("800x600")

        self.url_label = ttk.Label(master, text="请输入YouTube或Bilibili视频URL（每行一个）:")
        self.url_label.pack(pady=10)

        self.url_text = scrolledtext.ScrolledText(master, width=70, height=10)
        self.url_text.pack(pady=5)

        self.submit_button = ttk.Button(master, text="确认", command=self.process_urls)
        self.submit_button.pack(pady=10)

        self.progress_var = tk.StringVar()
        self.progress_label = ttk.Label(master, textvariable=self.progress_var)
        self.progress_label.pack(pady=5)

        self.history_label = ttk.Label(master, text="历史记录:")
        self.history_label.pack(pady=5)

        self.history_listbox = tk.Listbox(master, width=70, height=10)
        self.history_listbox.pack(pady=5)

        self.history_file = "unified_url_history.json"
        self.load_history()

    def process_urls(self):
        urls = self.url_text.get("1.0", tk.END).strip().split("\n")
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            messagebox.showerror("错误", "请输入至少一个有效的视频URL")
            return

        self.submit_button.config(state=tk.DISABLED)
        self.progress_var.set("处理中...")
        
        threading.Thread(target=self.process_urls_thread, args=(urls,), daemon=True).start()

    def process_urls_thread(self, urls):
        total = len(urls)
        success_count = 0
        for i, url in enumerate(urls, 1):
            self.master.after(0, self.update_progress, f"处理第 {i}/{total} 个视频...")
            video_title = self.get_subtitles(url)
            if video_title:
                self.add_to_history(url, video_title)
                success_count += 1
            else:
                self.master.after(0, self.update_progress, f"处理第 {i}/{total} 个视频失败")

        self.master.after(0, self.process_complete, success_count, total)

    def get_subtitles(self, url):
        if "youtube.com" in url or "youtu.be" in url:
            return get_youtube_subtitles(url)
        elif "bilibili.com" in url:
            return get_bilibili_subtitles(url)
        else:
            print(f"不支持的URL: {url}")
            return None

    def update_progress(self, message):
        self.progress_var.set(message)

    def process_complete(self, success_count, total):
        self.progress_var.set("处理完成")
        self.submit_button.config(state=tk.NORMAL)
        self.url_text.delete("1.0", tk.END)
        messagebox.showinfo("完成", f"处理完毕。成功：{success_count}/{total}。请查看控制台输出以获取详细信息。")

    def add_to_history(self, url, title):
        entry = {"url": url, "title": title}
        if entry not in self.history:
            self.history.insert(0, entry)
            self.history = self.history[:20]  # 保留最近的20个URL
            self.save_history()
            self.master.after(0, self.update_history_display)

    def load_history(self):
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                self.history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.history = []
        self.update_history_display()

    def save_history(self):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def update_history_display(self):
        self.history_listbox.delete(0, tk.END)
        for entry in self.history:
            self.history_listbox.insert(tk.END, f"{entry['title']} - {entry['url']}")

if __name__ == "__main__":
    root = tk.Tk()
    app = UnifiedSubtitleApp(root)
    root.mainloop()

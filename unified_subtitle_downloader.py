import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import json
from v1 import get_subtitles as get_youtube_subtitles
from bilibili_subtitle import get_subtitles as get_bilibili_subtitles

class UnifiedSubtitleDownloader:
    def __init__(self, master):
        self.master = master
        master.title("统一视频字幕下载器")
        master.geometry("800x700")  # 增加窗口高度以容纳历史记录

        self.history_file = "unified_url_history.json"
        self.history = []
        self.load_history()
        self.create_widgets()

    def create_widgets(self):
        self.url_label = ttk.Label(self.master, text="请输入视频URL（每行一个，支持YouTube和Bilibili）:")
        self.url_label.pack(pady=10)

        self.url_text = scrolledtext.ScrolledText(self.master, width=70, height=10)
        self.url_text.pack(pady=5)

        self.cookies_label = ttk.Label(self.master, text="Cookies文件 (可选，用于YouTube):")
        self.cookies_label.pack(pady=5)

        self.cookies_entry = ttk.Entry(self.master, width=50)
        self.cookies_entry.pack(pady=5)

        self.browse_button = ttk.Button(self.master, text="浏览", command=self.browse_cookies)
        self.browse_button.pack(pady=5)

        self.submit_button = ttk.Button(self.master, text="下载字幕", command=self.process_urls)
        self.submit_button.pack(pady=10)

        self.progress_var = tk.StringVar()
        self.progress_label = ttk.Label(self.master, textvariable=self.progress_var)
        self.progress_label.pack(pady=5)

        # 添加历史记录部分
        self.history_label = ttk.Label(self.master, text="历史记录:")
        self.history_label.pack(pady=5)

        self.history_listbox = tk.Listbox(self.master, width=70, height=10)
        self.history_listbox.pack(pady=5)

        self.update_history_display()

    def browse_cookies(self):
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if filename:
            self.cookies_entry.delete(0, tk.END)
            self.cookies_entry.insert(0, filename)

    def process_urls(self):
        urls = self.url_text.get("1.0", tk.END).strip().split("\n")
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            messagebox.showerror("错误", "请输入至少一个有效的视频URL")
            return

        cookies_file = self.cookies_entry.get()
        cookies = cookies_file if cookies_file else None

        self.submit_button.config(state=tk.DISABLED)
        self.progress_var.set("处理中...")
        
        threading.Thread(target=self.process_urls_thread, args=(urls, cookies), daemon=True).start()

    def process_urls_thread(self, urls, cookies):
        total = len(urls)
        for i, url in enumerate(urls, 1):
            self.master.after(0, self.update_progress, f"处理第 {i}/{total} 个视频...")
            if "youtube.com" in url or "youtu.be" in url:
                video_title = get_youtube_subtitles(url, cookies)
            elif "bilibili.com" in url or "b23.tv" in url:
                video_title = get_bilibili_subtitles(url)
            else:
                print(f"不支持的URL: {url}")
                continue

            if video_title:
                print(f"成功下载 '{video_title}' 的字幕")
                self.add_to_history(url, video_title)
            else:
                print(f"无法下载 '{url}' 的字幕")

        self.master.after(0, self.process_complete)

    def update_progress(self, message):
        self.progress_var.set(message)

    def process_complete(self):
        self.progress_var.set("处理完成")
        self.submit_button.config(state=tk.NORMAL)
        messagebox.showinfo("完成", "所有视频的字幕下载已完成")

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

    def save_history(self):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def update_history_display(self):
        self.history_listbox.delete(0, tk.END)
        for entry in self.history:
            self.history_listbox.insert(tk.END, f"{entry['title']} - {entry['url']}")

if __name__ == "__main__":
    root = tk.Tk()
    app = UnifiedSubtitleDownloader(root)
    root.mainloop()

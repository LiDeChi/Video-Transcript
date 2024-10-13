import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import re
import json
import os
import requests
import threading
from deep_translator import GoogleTranslator
import time
from requests.exceptions import RequestException

def extract_bvid(url):
    bvid_match = re.search(r"BV\w+", url)
    if bvid_match:
        return bvid_match.group(0)
    return None

def get_video_info(bvid):
    try:
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Origin': 'https://www.bilibili.com'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        print(f"Video info response: {data}")  # 打印完整的响应
        if data['code'] == 0:
            title = data['data']['title']
            aid = data['data']['aid']
            cid = data['data']['cid']
            return title, aid, cid
        else:
            print(f"获取视频信息失败，错误代码：{data['code']}，错误信息：{data['message']}")
            return None, None, None
    except Exception as e:
        print(f"获取视频信息时发生错误：{str(e)}")
        return None, None, None

def get_subtitle_url(bvid, cid):
    url = f"https://api.bilibili.com/x/player/v2?cid={cid}&bvid={bvid}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Origin': 'https://www.bilibili.com'
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    print(f"Subtitle info response: {data}")  # 打印完整的响应
    if data['code'] == 0 and 'subtitle' in data['data']:
        subtitles = data['data']['subtitle'].get('subtitles', [])
        if subtitles:
            return subtitles
        else:
            print("API返回的字幕列表为空")
    else:
        print(f"获取字幕信息失败，错误代码：{data['code']}，错误信息：{data.get('message', '未知错误')}")
    return None

def download_subtitle(bvid, cid, video_title):
    subtitles = get_subtitle_url(bvid, cid)
    if not subtitles:
        print(f"视频 (BV号：{bvid}) 没有可用的字幕")
        return False

    for subtitle in subtitles:
        language = subtitle['lan']
        subtitle_url = "https:" + subtitle['subtitle_url']
        save_subtitle(bvid, video_title, subtitle_url, language)
    
    return True

def save_subtitle(bvid, video_title, subtitle_url, language):
    try:
        response = requests.get(subtitle_url)
        response.raise_for_status()
        subtitle_data = response.json()
        
        if not os.path.exists('subtitles'):
            os.makedirs('subtitles')
        
        safe_title = re.sub(r'[\\/*?:"<>|]', "", video_title)
        filename = f"subtitles/{safe_title}_{language}.srt"
        with open(filename, 'w', encoding='utf-8') as f:
            for i, line in enumerate(subtitle_data['body'], start=1):
                start_time = format_time(line['from'])
                end_time = format_time(line['to'])
                content = line['content']
                f.write(f"{i}\n{start_time} --> {end_time}\n{content}\n\n")
        
        print(f"字幕已保存到 {filename}")
    except Exception as e:
        print(f"保存字幕时发生错误：{str(e)}")

def format_time(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace('.', ',')

def get_subtitles(video_url):
    bvid = extract_bvid(video_url)
    if not bvid:
        print(f"无效的Bilibili URL: {video_url}")
        return None

    try:
        video_title, aid, cid = get_video_info(bvid)
        if not video_title or not aid or not cid:
            print(f"无法获取视频信息，BV号：{bvid}")
            return None

        if download_subtitle(bvid, cid, video_title):
            return video_title
        else:
            print(f"无法下载字幕，视频标题：{video_title}")
            return None

    except Exception as e:
        print(f"获取字幕时发生未知错误：{str(e)}")
        return None

class BilibiliSubtitleApp:
    def __init__(self, master):
        self.master = master
        master.title("Bilibili字幕下载器")
        master.geometry("800x600")

        self.url_label = ttk.Label(master, text="请输入Bilibili视频URL（每行一个）:")
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

        self.history_file = "bilibili_url_history.json"
        self.load_history()

    def process_urls(self):
        urls = self.url_text.get("1.0", tk.END).strip().split("\n")
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            messagebox.showerror("错误", "请输入至少一个有效的Bilibili URL")
            return

        self.submit_button.config(state=tk.DISABLED)
        self.progress_var.set("处理中...")
        
        threading.Thread(target=self.process_urls_thread, args=(urls,), daemon=True).start()

    def process_urls_thread(self, urls):
        total = len(urls)
        for i, url in enumerate(urls, 1):
            self.master.after(0, self.update_progress, f"处理第 {i}/{total} 个视频...")
            video_title = get_subtitles(url)
            if video_title:
                self.add_to_history(url, video_title)

        self.master.after(0, self.process_complete)

    def update_progress(self, message):
        self.progress_var.set(message)

    def process_complete(self):
        self.progress_var.set("处理完成")
        self.submit_button.config(state=tk.NORMAL)
        self.url_text.delete("1.0", tk.END)
        messagebox.showinfo("成", "所有视频的字幕和文本文件已生成")

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
    app = BilibiliSubtitleApp(root)
    root.mainloop()

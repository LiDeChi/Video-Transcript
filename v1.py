import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re
import json
import os
import requests
import random

# 添加一个用户代理列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def extract_video_id(url):
    # 从YouTube URL中提取视频ID
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:embed\/|v\/|youtu.be\/)([0-9A-Za-z_-]{11})",
        r"^([0-9A-Za-z_-]{11})$"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    print(f"无法从URL提取视频ID: {url}")
    return None

def get_video_title(video_id):
    try:
        url = f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json"
        headers = {'User-Agent': get_random_user_agent()}
        response = requests.get(url, headers=headers)
        data = response.json()
        return data['title']
    except:
        return video_id  # 如果获取标题失败,就使用视频ID作为标题

def get_subtitles(video_url, cookies=None):
    video_id = extract_video_id(video_url)
    if not video_id:
        print("无效的YouTube URL")
        return None

    try:
        video_title = get_video_title(video_id)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookies)
        
        # 尝试获取原始字幕
        original_transcript = None
        for transcript in transcript_list:
            original_transcript = transcript
            break  # 获取第一个可用的字幕
        
        if original_transcript:
            print(f"找到原始字幕，语言：{original_transcript.language}")
            save_subtitle(video_id, video_title, original_transcript, original_transcript.language)
            
            # 尝试翻译成中文
            chinese_codes = ['zh', 'zh-CN', 'zh-TW', 'zh-HK', 'zh-SG', 'zh-Hans', 'zh-Hant']
            translated = False
            
            for code in chinese_codes:
                try:
                    zh_translated = original_transcript.translate(code)
                    save_subtitle(video_id, video_title, zh_translated, f'{code}-translated')
                    print(f"已将原始字幕翻译为中文（{code}）并保存")
                    translated = True
                    break
                except Exception as e:
                    print(f"使用 '{code}' 翻译字幕时出错: {str(e)}")
            
            if not translated:
                print("尝试了所有中文语言代码，但都无法成功翻译")
        else:
            print(f"视频 '{video_title}' 没有可用的字幕")
        
        return video_title
        
    except TranscriptsDisabled:
        print(f"视频 '{video_title}' 的字幕已被禁用。尝试使用cookies可能会解决此问题。")
        return None
    except NoTranscriptFound:
        print(f"视频 '{video_title}' 没有找到字幕。尝试使用cookies可能会解决此问题。")
        return None
    except Exception as e:
        print(f"获取字幕时出错: {str(e)}")
        print(f"视频ID: {video_id}")
        print(f"视频标题: {video_title}")
        print(f"建议：访问 https://www.youtube.com/watch?v={video_id} 查看更多信息")
        return None

def save_subtitle(video_id, video_title, transcript, language):
    safe_title = re.sub(r'[\\/*?:"<>|]', "", video_title)  # 移除文件名中的非法字符
    srt_filename = f"{safe_title}_{language}_subtitles.srt"
    with open(srt_filename, "w", encoding="utf-8") as f:
        for i, entry in enumerate(transcript.fetch(), start=1):
            start = entry['start']
            duration = entry['duration']
            end = start + duration
            text = entry['text']
            
            f.write(f"{i}\n")
            f.write(f"{format_time(start)} --> {format_time(end)}\n")
            f.write(f"{text}\n\n")
    
    print(f"{language}字幕已保存到 {srt_filename}")
    
    create_consolidated_text(video_id, video_title, transcript, language)

def create_consolidated_text(video_id, video_title, transcript, language):
    safe_title = re.sub(r'[\\/*?:"<>|]', "", video_title)  # 移除文件名中的非法字符
    txt_filename = f"{safe_title}_{language}_consolidated.txt"
    
    consolidated_text = ""
    paragraph = ""
    sentence_count = 0
    last_end_time = 0
    is_first_paragraph = True
    
    for entry in transcript.fetch():
        text = entry['text'].strip()
        start_time = entry['start']
        
        # 如果与上一个字幕的时间间隔超过5秒，或者累积了3个句子，就开始新的段落
        if start_time - last_end_time > 5 or sentence_count >= 3:
            if paragraph:
                if not is_first_paragraph:
                    consolidated_text += "\n\n"  # 段落之间空两行
                consolidated_text += paragraph.strip() + "\n"  # 移除段落首的缩进
                is_first_paragraph = False
                paragraph = ""
                sentence_count = 0
        
        paragraph += text + " "
        last_end_time = start_time + entry['duration']
        
        # 检查是否有句子结束符
        if language.startswith('zh'):
            # 对于中文，我们检查常见的句子结束符
            if text.endswith('。') or text.endswith('！') or text.endswith('？') or text.endswith('…'):
                sentence_count += 1
        else:
            # 对于其他语言（如英文），保持原有的检查方式
            if text.endswith('.') or text.endswith('?') or text.endswith('!'):
                sentence_count += 1
    
    # 写入最后剩余的文本
    if paragraph:
        if not is_first_paragraph:
            consolidated_text += "\n\n"
        consolidated_text += paragraph.strip()
    
    # 保存文本文件
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(consolidated_text)
    
    print(f"整合并分段后的{language}文本已保存到 {txt_filename}")

def format_time(seconds):
    # 将秒数转换为SRT时间格式 (HH:MM:SS,mmm)
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

class YouTubeSubtitleApp:
    def __init__(self, master):
        self.master = master
        master.title("YouTube字幕下载器")
        master.geometry("600x500")

        self.url_label = ttk.Label(master, text="请输入YouTube视频URL:")
        self.url_label.pack(pady=10)

        self.url_entry = ttk.Entry(master, width=50)
        self.url_entry.pack(pady=5)

        self.cookies_label = ttk.Label(master, text="Cookies文件 (可选，但推荐使用):")
        self.cookies_label.pack(pady=5)

        self.cookies_entry = ttk.Entry(master, width=50)
        self.cookies_entry.pack(pady=5)

        self.browse_button = ttk.Button(master, text="浏览", command=self.browse_cookies)
        self.browse_button.pack(pady=5)

        self.submit_button = ttk.Button(master, text="下载字幕", command=self.process_url)
        self.submit_button.pack(pady=10)

        self.status_label = ttk.Label(master, text="")
        self.status_label.pack(pady=5)

        self.history_label = ttk.Label(master, text="历史记录:")
        self.history_label.pack(pady=5)

        self.history_listbox = tk.Listbox(master, width=70, height=10)
        self.history_listbox.pack(pady=5)

        self.history_file = "youtube_url_history.json"
        self.load_history()

    def browse_cookies(self):
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if filename:
            self.cookies_entry.delete(0, tk.END)
            self.cookies_entry.insert(0, filename)

    def process_url(self):
        url = self.url_entry.get()
        cookies_file = self.cookies_entry.get()
        
        if url:
            cookies = None
            if cookies_file:
                cookies = cookies_file
            
            self.status_label.config(text="正在下载字幕...")
            self.master.update()
            
            video_title = get_subtitles(url, cookies=cookies)
            if video_title:
                self.add_to_history(url, video_title)
                self.status_label.config(text="字幕下载成功！")
                messagebox.showinfo("成功", "字幕和文本文件已生成")
                self.url_entry.delete(0, tk.END)  # 清空输入框
            else:
                self.status_label.config(text="字幕下载失败。请查看控制台输出以获取详细信息。")
                messagebox.showwarning("警告", "无法获取字幕。请查看控制台输出以获取详细信息。")
        else:
            self.status_label.config(text="请输入有效的YouTube URL")
            messagebox.showerror("错误", "请输入有效的YouTube URL")

    def add_to_history(self, url, title):
        entry = {"url": url, "title": title}
        if entry not in self.history:
            self.history.insert(0, entry)
            self.history = self.history[:20]  # 保留最近的20个URL
            self.save_history()
            self.update_history_display()

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
    app = YouTubeSubtitleApp(root)
    root.mainloop()
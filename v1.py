import tkinter as tk
from tkinter import ttk, messagebox
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json
import os
import requests

def extract_video_id(url):
    # 从YouTube URL中提取视频ID
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def get_video_title(video_id):
    try:
        url = f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(url)
        data = response.json()
        return data['title']
    except:
        return video_id  # 如果获取标题失败,就使用视频ID作为标题

def get_subtitles(video_url):
    video_id = extract_video_id(video_url)
    if not video_id:
        print("无效的YouTube URL")
        return

    try:
        video_title = get_video_title(video_id)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        zh_transcript = None
        en_transcript = None
        
        try:
            zh_transcript = transcript_list.find_transcript(['zh-CN', 'zh'])
        except:
            print("未找到中文字幕")
        
        try:
            en_transcript = transcript_list.find_transcript(['en'])
        except:
            if not zh_transcript:
                print("未找到英文字幕")
        
        if zh_transcript:
            save_subtitle(video_id, video_title, zh_transcript, 'zh-CN')
        
        if en_transcript:
            save_subtitle(video_id, video_title, en_transcript, 'en')
        
        if not zh_transcript and not en_transcript:
            print("未找到中文或英文字幕")
        
        return video_title
        
    except Exception as e:
        print(f"获取字幕时出错: {str(e)}")
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
        master.geometry("600x400")

        self.url_label = ttk.Label(master, text="请输入YouTube视频URL:")
        self.url_label.pack(pady=10)

        self.url_entry = ttk.Entry(master, width=50)
        self.url_entry.pack(pady=5)

        self.submit_button = ttk.Button(master, text="确认", command=self.process_url)
        self.submit_button.pack(pady=10)

        self.history_label = ttk.Label(master, text="历史记录:")
        self.history_label.pack(pady=5)

        self.history_listbox = tk.Listbox(master, width=70, height=10)
        self.history_listbox.pack(pady=5)

        self.history_file = "youtube_url_history.json"
        self.load_history()

    def process_url(self):
        url = self.url_entry.get()
        if url:
            video_title = get_subtitles(url)
            if video_title:
                self.add_to_history(url, video_title)
                messagebox.showinfo("成功", "字幕和文本文件已生成")
                self.url_entry.delete(0, tk.END)  # 清空输入框
            else:
                messagebox.showerror("错误", "无法获取视频信息或生成字幕")
        else:
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

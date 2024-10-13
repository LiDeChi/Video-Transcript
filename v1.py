from youtube_transcript_api import YouTubeTranscriptApi
import re

def extract_video_id(url):
    # 从YouTube URL中提取视频ID
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def get_subtitles(video_url):
    video_id = extract_video_id(video_url)
    if not video_id:
        print("无效的YouTube URL")
        return

    try:
        # 尝试获取所有可用的字幕
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 优先尝试获取中文字幕
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
            save_subtitle(video_id, zh_transcript, 'zh-CN')
        
        if en_transcript:
            save_subtitle(video_id, en_transcript, 'en')
        
        if not zh_transcript and not en_transcript:
            print("未找到中文或英文字幕")
        
    except Exception as e:
        print(f"获取字幕时出错: {str(e)}")

def save_subtitle(video_id, transcript, language):
    # 将字幕保存为SRT格式
    srt_filename = f"{video_id}_{language}_subtitles.srt"
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
    
    # 生成整合后的文本文件
    create_consolidated_text(video_id, transcript, language)
    
    # 生成Markdown文件
    create_markdown_text(video_id, transcript, language)

def create_consolidated_text(video_id, transcript, language):
    txt_filename = f"{video_id}_{language}_consolidated.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
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
                        f.write("\n\n")  # 段落之间空两行
                    f.write("    " + paragraph.strip() + "\n")  # 段落首个单词缩进
                    is_first_paragraph = False
                    paragraph = ""
                    sentence_count = 0
            
            paragraph += text + " "
            last_end_time = start_time + entry['duration']
            
            # 检查是否有句子结束符
            if text.endswith('.') or text.endswith('?') or text.endswith('!'):
                sentence_count += 1
        
        # 写入最后剩余的文本
        if paragraph:
            if not is_first_paragraph:
                f.write("\n\n")
            f.write("    " + paragraph.strip())
    
    print(f"整合并分段后的{language}文本已保存到 {txt_filename}")

def create_markdown_text(video_id, transcript, language):
    md_filename = f"{video_id}_{language}_consolidated.md"
    with open(md_filename, "w", encoding="utf-8") as f:
        paragraph = ""
        sentence_count = 0
        last_end_time = 0
        
        # 写入标题
        f.write(f"# Transcript: {video_id}\n\n")
        
        for entry in transcript.fetch():
            text = entry['text'].strip()
            start_time = entry['start']
            
            # 如果与上一个字幕的时间间隔超过5秒，或者累积了3个句子，就开始新的段落
            if start_time - last_end_time > 5 or sentence_count >= 3:
                if paragraph:
                    f.write(paragraph.strip() + "\n\n\n")  # 段落之间空两行
                    f.write(f"## {format_time(start_time)}\n\n")  # 添加时间戳作为二级标题
                paragraph = ""
                sentence_count = 0
            
            paragraph += text + " "
            last_end_time = start_time + entry['duration']
            
            # 检查是否有句子结束符
            if text.endswith('.') or text.endswith('?') or text.endswith('!'):
                sentence_count += 1
        
        # 写入最后剩余的文本
        if paragraph:
            f.write(paragraph.strip())
    
    print(f"整合并分段后的{language} Markdown 文件已保存到 {md_filename}")

def format_time(seconds):
    # 将秒数转换为SRT时间格式 (HH:MM:SS,mmm)
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

if __name__ == "__main__":
    video_url = input("请输入YouTube视频URL: ")
    get_subtitles(video_url)

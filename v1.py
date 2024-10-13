from youtube_transcript_api import YouTubeTranscriptApi
import re

def extract_video_id(url):
    # 从YouTube URL中提取视频ID
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def get_subtitles(video_url, language='zh-CN'):
    video_id = extract_video_id(video_url)
    if not video_id:
        print("无效的YouTube URL")
        return

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        
        # 将字幕保存为SRT格式
        with open(f"{video_id}_{language}_subtitles.srt", "w", encoding="utf-8") as f:
            for i, entry in enumerate(transcript, start=1):
                start = entry['start']
                duration = entry['duration']
                end = start + duration
                text = entry['text']
                
                f.write(f"{i}\n")
                f.write(f"{format_time(start)} --> {format_time(end)}\n")
                f.write(f"{text}\n\n")
        
        print(f"字幕已保存到 {video_id}_{language}_subtitles.srt")
    except Exception as e:
        print(f"获取字幕时出错: {str(e)}")

def format_time(seconds):
    # 将秒数转换为SRT时间格式 (HH:MM:SS,mmm)
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

if __name__ == "__main__":
    video_url = input("请输入YouTube视频URL: ")
    language = input("请选择字幕语言 (zh-CN 为中文, en 为英文): ").strip().lower()
    if language not in ['zh-cn', 'en']:
        print("不支持的语言,默认使用中文")
        language = 'zh-CN'
    elif language == 'en':
        language = 'en'
    get_subtitles(video_url, language)

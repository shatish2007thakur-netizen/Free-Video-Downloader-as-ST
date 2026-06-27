import streamlit as st
import yt_dlp
import os
import re
import zipfile
import io

# Set website layout and title
st.set_page_config(page_title="Universal Video Downloader", page_icon="🎬", layout="centered")

st.title("🎬 Universal Video Downloader")
st.write("Paste your favorite video or playlist link below to download directly.")

# Initialize session state variables
if "download_ready" not in st.session_state:
    st.session_state.download_ready = False
    st.session_state.file_data = None
    st.session_state.file_name = ""
    st.session_state.mime_type = ""
    st.session_state.meta_url = ""

# Progress bar hook callback for yt-dlp
def progress_hook(d):
    if d['status'] == 'downloading':
        percent_str = d.get('_percent_str', '0%')
        clean_percent = re.sub(r'\x1b\[[0-9;]*m', '', percent_str).strip().replace('%', '')
        try:
            progress = float(clean_percent) / 100.0
            progress = max(0.0, min(1.0, progress))
            progress_bar.progress(progress, text=f"Downloading item: {percent_str.strip()}")
        except ValueError:
            pass
    elif d['status'] == 'finished':
        progress_bar.progress(1.0, text="Processing item...")

# Convert seconds to readable HH:MM:SS format
def format_duration(seconds):
    if not seconds:
        return "Unknown"
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

# Get URL input from the user
url = st.text_input("Paste video or playlist link:", placeholder="https://...")

if url != st.session_state.meta_url:
    st.session_state.download_ready = False
    st.session_state.meta_url = url

# बेस ऑप्शन्स जो यूट्यूब के ब्लॉक को रोकने में मदद करेंगे
BASE_YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': True,
    'nocheckcertificate': True,
    'legacy_server_connect': True,
    # यह सर्वर को ब्लॉक होने से बचाने के लिए क्रोम ब्राउज़र की तरह दिखाता है
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
}

if url:
    is_playlist = False
    playlist_title = "Playlist"
    
    # 1. Fetch Metadata and Detect Playlist Structure
    with st.spinner("Analyzing link..."):
        try:
            with yt_dlp.YoutubeDL(BASE_YDL_OPTS) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Check if it's a playlist containing entries
                if 'entries' in info:
                    is_playlist = True
                    playlist_title = info.get('title', 'Playlist')
                    entries = list(info['entries'])
                    video_count = len(entries)
                    
                    st.info(f"📂 **Playlist Detected:** {playlist_title} ({video_count} items found)")
                else:
                    # Single video preview layout
                    col1, col2 = st.columns()
                    with col1:
                        thumbnail = info.get('thumbnail') or info.get('thumbnails', [{}])[0].get('url')
                        if thumbnail:
                            st.image(thumbnail, use_container_width=True)
                    with col2:
                        st.subheader(info.get('title', 'Video Preview'))
                        st.write(f"👤 **Channel:** {info.get('uploader', 'Unknown')}")
                        st.write(f"⏱️ **Duration:** {format_duration(info.get('duration'))}")
                        
        except Exception as e:
            err_msg = str(e).lower()
            if "private" in err_msg:
                st.error("🔒 Error: This content is private.")
            elif "sign in" in err_msg or "age" in err_msg:
                st.error("🔞 Error: This content is age-restricted.")
            else:
                st.error("❌ Error: Unable to fetch details. Server might be rate-limited by YouTube.")

    # 2. Format Selections UI
    download_type = st.selectbox("Select Download Type:", ["Video (MP4)", "Audio Only (MP3)"])

    video_quality = "best"
    if download_type == "Video (MP4)":
        quality_choice = st.selectbox("Select Video Quality:", ["Best Available", "1080p", "720p", "480p"])
        quality_map = {
            "Best Available": "bestvideo+bestaudio/best",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]"
        }
        video_quality = quality_map[quality_choice]

    # 3. Download Execution Core
    if st.button("Prepare Download", type="primary"):
        progress_bar = st.progress(0.0, text="Initializing...")
        status_text = st.empty()
        
        # Safe directory initialization for output compilation
        output_dir = "downloads_temp"
        os.makedirs(output_dir, exist_ok=True)
        
        # बेस हेडर को डाउनलोड ऑप्शन्स में मर्ज करना
        ydl_opts = BASE_YDL_OPTS.copy()
        ydl_opts.update({
            'extract_flat': False, # डाउनलोड के समय पूरा डेटा चाहिए
            'progress_hooks': [progress_hook],
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        })
        
        if download_type == "Audio Only (MP3)":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts.update({
                'format': video_quality,
                'merge_output_format': 'mp4',
            })
            
        if is_playlist:
            ydl_opts['noplaylist'] = False
        else:
            ydl_opts['noplaylist'] = True

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                status_text.text("Downloading from source server...")
                info_data = ydl.extract_info(url, download=True)
            
            # Gather all downloaded items inside the temp directory
            downloaded_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir)]
            
            if not downloaded_files:
                raise Exception("No files were successfully downloaded.")

            if is_playlist:
                status_text.text("Packaging items into a ZIP file...")
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for file_path in downloaded_files:
                        zip_file.write(file_path, os.path.basename(file_path))
                
                st.session_state.file_data = zip_buffer.getvalue()
                st.session_state.file_name = f"{playlist_title}.zip"
                st.session_state.mime_type = "application/zip"
            else:
                single_file = downloaded_files[0]
                with open(single_file, "rb") as file:
                    st.session_state.file_data = file.read()
                st.session_state.file_name = os.path.basename(single_file)
                st.session_state.mime_type = "audio/mp3" if download_type == "Audio Only (MP3)" else "video/mp4"

            # Clean up local temporary files and directory entirely
            for file_path in downloaded_files:
                os.remove(file_path)
            os.rmdir(output_dir)
            
            st.session_state.download_ready = True
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Processing failed: YouTube might be blocking the cloud server. Try a different video or lower quality.")
            st.session_state.download_ready = False

    # 4. Persistent Global Asset Downloader Trigger
    if st.session_state.download_ready:
        st.success(f"🎉 Ready to download: {st.session_state.file_name}")
        st.download_button(
            label="💾 Click Here to Download",
            data=st.session_state.file_data,
            file_name=st.session_state.file_name,
            mime=st.session_state.mime_type
        )

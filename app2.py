import streamlit as st
from pytube import YouTube, Playlist
import os
import zipfile
import io

st.set_page_config(page_title="Universal Video Downloader", page_icon="🎬", layout="centered")
st.title("🎬 Universal Video Downloader")
st.write("Paste your favorite YouTube video or playlist link below.")

url = st.text_input("Paste video or playlist link:", placeholder="https://...")

if url:
    try:
        with st.spinner("Analyzing link..."):
            # प्लेलिस्ट चेक करना
            if "playlist" in url.lower():
                pl = Playlist(url)
                st.info(f"📂 **Playlist Detected:** {pl.title} ({len(pl.video_urls)} items)")
                video_list = list(pl.videos)
                is_playlist = True
            else:
                yt = YouTube(url)
                is_playlist = False
                
                col1, col2 = st.columns()
                with col1:
                    st.image(yt.thumbnail_url, use_container_width=True)
                with col2:
                    st.subheader(yt.title)
                    st.write(f"⏱️ **Duration:** {yt.length} seconds")

        download_type = st.selectbox("Select Download Type:", ["Video (MP4)", "Audio Only (MP3)"])

        if st.button("Prepare Download", type="primary"):
            progress_bar = st.progress(0.0, text="Downloading...")
            output_dir = "downloads_temp"
            os.makedirs(output_dir, exist_ok=True)

            if is_playlist:
                # प्लेलिस्ट डाउनलोड लॉजिक
                for idx, video in enumerate(video_list[:5]): # लिमिट पहली 5 वीडियो तक
                    if download_type == "Audio Only (MP3)":
                        stream = video.streams.get_audio_only()
                    else:
                        stream = video.streams.get_highest_resolution()
                    stream.download(output_path=output_dir)
                    progress_bar.progress((idx + 1) / min(5, len(video_list)))

                # ज़िप फ़ाइल बनाना
                zip_buffer = io.BytesIO()
                downloaded_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir)]
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for file_path in downloaded_files:
                        zip_file.write(file_path, os.path.basename(file_path))
                
                st.success("🎉 Playlist Ready!")
                st.download_button("💾 Download ZIP", data=zip_buffer.getvalue(), file_name="playlist.zip", mime="application/zip")
            else:
                # सिंगल वीडियो डाउनलोड लॉजिक
                if download_type == "Audio Only (MP3)":
                    stream = yt.streams.get_audio_only()
                    file_name = f"{yt.title}.mp3"
                    mime = "audio/mp3"
                else:
                    stream = yt.streams.get_highest_resolution()
                    file_name = f"{yt.title}.mp4"
                    mime = "video/mp4"
                
                saved_path = stream.download(output_path=output_dir)
                with open(saved_path, "rb") as file:
                    file_bytes = file.read()
                
                st.success("🎉 Video Ready!")
                st.download_button("💾 Download File", data=file_bytes, file_name=file_name, mime=mime)

            # क्लीनअप
            if os.path.exists(output_dir):
                for f in os.listdir(output_dir):
                    os.remove(os.path.join(output_dir, f))
                os.rmdir(output_dir)

    except Exception as e:
        st.error(f"❌ Error: Cloud server is heavily restricted. Try another link or try after some time.")

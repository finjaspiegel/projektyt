import streamlit as st
from googleapiclient.discovery import build
import re
import pandas as pd
import matplotlib.pyplot as plt

# YouTube API einrichten
API_KEY = "DEIN_API_SCHLÜSSEL"
youtube = build("youtube", "v3", developerKey=API_KEY)

# Extrahiere die Kanal-ID
def extract_channel_id(channel_input):
    if "youtube.com/channel/" in channel_input:
        match = re.search(r"channel/([a-zA-Z0-9_-]+)", channel_input)
        return match.group(1) if match else None

    if "@" in channel_input:
        channel_input = channel_input.replace("https://www.youtube.com/", "").replace("@", "")

    request = youtube.search().list(
        q=channel_input,
        part="snippet",
        type="channel",
        maxResults=1
    )
    response = request.execute()
    if not response["items"]:
        return None

    return response["items"][0]["id"]["channelId"]

# Hol die Upload-Playlist-ID
def get_uploads_playlist_id(channel_id):
    request = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    )
    response = request.execute()
    return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

# Hol Videos und Statistiken
def get_videos_with_stats(playlist_id, max_results=5):
    valid_videos = []
    next_page_token = None

    while len(valid_videos) < max_results:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=10,
            pageToken=next_page_token
        )
        response = request.execute()

        if "items" not in response or not response["items"]:
            break

        video_ids = [item["contentDetails"]["videoId"] for item in response["items"]]

        video_details_request = youtube.videos().list(
            part="contentDetails,snippet,statistics",
            id=",".join(video_ids)
        )
        video_details_response = video_details_request.execute()

        for video in video_details_response["items"]:
            duration = video["contentDetails"]["duration"]
            title = video["snippet"]["title"]
            video_id = video["id"]
            statistics = video["statistics"]

            if "PT" in duration:
                minutes = int(re.search(r"(\d+)M", duration).group(1)) if "M" in duration else 0
                seconds = int(re.search(r"(\d+)S", duration).group(1)) if "S" in duration else 0
                total_seconds = minutes * 60 + seconds

                if total_seconds >= 180:
                    views = int(statistics.get("viewCount", 0))
                    likes = int(statistics.get("likeCount", 0))
                    valid_videos.append({"title": title, "video_id": video_id, "views": views, "likes": likes})

                    if len(valid_videos) == max_results:
                        break

        next_page_token = response.get("nextPageToken", None)
        if not next_page_token:
            break

    return valid_videos

# Streamlit-Interface
st.title("YouTube Channel Vergleich mit Statistik")

# Eingabe der Kanäle
channel_inputs = []
col = st.columns(5)
for i in range(5):
    with col[i]:
        channel_input = st.text_input(f"Kanal {i+1} (Name, Link, @Name):", key=f"channel_input_{i}")
        if channel_input:
            channel_inputs.append(channel_input)

max_results = st.slider("Anzahl der Videos", min_value=1, max_value=20, value=5)

# Statistiken berechnen
channel_stats = []
video_data = {}

for channel_input in channel_inputs:
    channel_id = extract_channel_id(channel_input)
    if channel_id:
        playlist_id = get_uploads_playlist_id(channel_id)
        videos = get_videos_with_stats(playlist_id, max_results)

        if videos:
            total_views = sum(video["views"] for video in videos)
            average_views = total_views / len(videos)
            average_likes = sum(video["likes"] for video in videos) / len(videos)
            channel_stats.append({"Channel": channel_input, 
                                  "Avg Views": average_views, 
                                  "Avg Likes": average_likes, 
                                  "Total Views": total_views})
            video_data[channel_input] = videos

# Tabelle anzeigen
if channel_stats:
    st.subheader("Statistiken der YouTube-Kanäle")
    df = pd.DataFrame(channel_stats)
    st.table(df)

# Graph anzeigen
if video_data:
    st.subheader("Verlauf der Aufrufe der letzten Videos")
    fig, ax = plt.subplots()

    for channel_name, videos in video_data.items():
        views = [video["views"] for video in videos]
        titles = [video["title"] for video in videos]
        ax.plot(titles, views, marker='o', label=channel_name)

    ax.set_xlabel("Videos")
    ax.set_ylabel("Aufrufe")
    ax.set_title("Verlauf der Videoaufrufe")
    ax.legend()
    plt.xticks(rotation=45)
    st.pyplot(fig)
